"""Unit tests for the broker admission-control middleware (§04 R1).

Past ``max_in_flight`` the next request is shed with ``503`` + ``Retry-After``
without queuing; infra routes (``/health``, ``/metrics``) are never gated; slots
release after the in-flight request completes.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi import FastAPI

from jentic_one.broker.web.middleware import AdmissionControlMiddleware, _AdmissionGate


def _app(*, max_in_flight: int, gate: asyncio.Event | None = None) -> FastAPI:
    app = FastAPI()

    @app.get("/slow")
    async def slow() -> dict[str, str]:
        if gate is not None:
            await gate.wait()
        return {"status": "ok"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(AdmissionControlMiddleware, max_in_flight=max_in_flight, retry_after_s=7)
    return app


def _client(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_sheds_503_with_retry_after_past_cap() -> None:
    gate = asyncio.Event()
    app = _app(max_in_flight=1, gate=gate)
    async with _client(app) as client:
        # Occupy the only slot with a request held open by the gate.
        held = asyncio.create_task(client.get("/slow"))
        await asyncio.sleep(0.05)

        shed = await client.get("/slow")
        assert shed.status_code == 503
        assert shed.headers["retry-after"] == "7"
        assert shed.headers["content-type"] == "application/problem+json"
        assert shed.json()["status"] == 503

        # Release the held request; the slot frees and the next request succeeds.
        gate.set()
        assert (await held).status_code == 200

        ok = await client.get("/slow")
        assert ok.status_code == 200


@pytest.mark.asyncio
async def test_health_excluded_even_while_shedding() -> None:
    gate = asyncio.Event()
    app = _app(max_in_flight=1, gate=gate)
    async with _client(app) as client:
        held = asyncio.create_task(client.get("/slow"))
        await asyncio.sleep(0.05)

        # The single slot is occupied — a /slow would shed — but /health is
        # never gated and must still answer 200.
        shed = await client.get("/slow")
        assert shed.status_code == 503

        health = await client.get("/health")
        assert health.status_code == 200

        gate.set()
        await held


@pytest.mark.asyncio
async def test_connection_close_stamped_while_draining() -> None:
    # During drain the middleware stamps Connection: close so a keep-alive
    # client/LB tears the connection down and re-resolves to a healthy pod
    # (§09 E4.3). A non-draining gate leaves the header untouched.
    admission_gate = _AdmissionGate(max_in_flight=5)
    app = FastAPI()

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(
        AdmissionControlMiddleware, max_in_flight=5, retry_after_s=7, gate=admission_gate
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        normal = await client.get("/ping")
        assert normal.headers.get("connection", "").lower() != "close"

        admission_gate.start_draining()
        draining = await client.get("/ping")
        assert draining.status_code == 200
        assert draining.headers["connection"].lower() == "close"
