"""Unit tests for the saturation-aware readiness probe (§05 R5.2).

``/ready`` reports ``200`` below the saturation threshold and flips to ``503``
once in-flight nears the admission cap, reading the same ``_AdmissionGate`` the
shedding middleware counts on. A missing gate (minimal app) reports ready.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from jentic_one.broker.web.middleware import _AdmissionGate
from jentic_one.broker.web.readiness import make_readiness_router


def _app(gate: _AdmissionGate | None, *, threshold: float | None = None) -> FastAPI:
    app = FastAPI()
    router = (
        make_readiness_router(saturation_threshold=threshold)
        if threshold is not None
        else make_readiness_router()
    )
    app.include_router(router)
    if gate is not None:
        app.state.broker_admission_gate = gate
    return app


def _client(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_ready_when_below_threshold() -> None:
    gate = _AdmissionGate(max_in_flight=10)
    gate.in_flight = 5  # 0.5 saturation, below the 0.9 threshold
    async with _client(_app(gate)) as client:
        resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_unready_when_saturated() -> None:
    gate = _AdmissionGate(max_in_flight=10)
    gate.in_flight = 9  # 0.9 saturation, at the threshold
    async with _client(_app(gate)) as client:
        resp = await client.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "unready"
    assert body["reason"] == "saturated"


@pytest.mark.asyncio
async def test_ready_without_gate() -> None:
    async with _client(_app(None)) as client:
        resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_configurable_threshold() -> None:
    # A lower threshold flips unready earlier; the same load that is "ready" at
    # 0.9 is "unready" at 0.5.
    gate = _AdmissionGate(max_in_flight=10)
    gate.in_flight = 6  # 0.6 saturation

    async with _client(_app(gate, threshold=0.9)) as client:
        assert (await client.get("/ready")).status_code == 200

    async with _client(_app(gate, threshold=0.5)) as client:
        resp = await client.get("/ready")
    assert resp.status_code == 503
    assert resp.json()["reason"] == "saturated"


@pytest.mark.asyncio
async def test_unready_when_draining_regardless_of_saturation() -> None:
    # A draining instance reports unready even at zero load, so the LB
    # deregisters it before the graceful drain (§09 E4.3).
    gate = _AdmissionGate(max_in_flight=10)
    gate.in_flight = 0
    gate.start_draining()
    async with _client(_app(gate)) as client:
        resp = await client.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "unready"
    assert body["reason"] == "draining"
