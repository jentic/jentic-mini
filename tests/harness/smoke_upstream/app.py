"""Test-only "smoke upstream" FastAPI app.

A self-contained, auth-less, DB-less HTTP mirror used to validate the broker's
proxying, credential injection, resilience, and streaming behaviour. It is
deliberately independent of the production package (``jentic_one``): nothing
here imports control-plane metadata or wiring.

Importable as ``tests.harness.smoke_upstream.app``; ``build_smoke_app`` returns
a fresh app so tests can compose ASGI transports without shared global state.
"""

from __future__ import annotations

from fastapi import FastAPI

from tests.harness.smoke_upstream.mock_control import MockControlMiddleware
from tests.harness.smoke_upstream.routers import (
    auth,
    behavior,
    callbacks,
    drift,
    edge,
    lifecycle,
    limits,
    live_spec,
    pagination,
    parameters,
    servers,
    specs,
    webhooks,
)


def build_smoke_app() -> FastAPI:
    app = FastAPI(title="Smoke Upstream")
    app.add_middleware(MockControlMiddleware)
    app.include_router(behavior.router)
    app.include_router(auth.router)
    app.include_router(edge.router)
    app.include_router(parameters.router)
    app.include_router(callbacks.router)
    app.include_router(drift.router)
    app.include_router(specs.router)
    app.include_router(pagination.router)
    app.include_router(webhooks.router)
    app.include_router(servers.router)
    app.include_router(limits.router)
    app.include_router(lifecycle.router)
    app.include_router(live_spec.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
