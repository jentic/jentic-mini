"""Shared health-check router factory for surfaces without bespoke health logic."""

from __future__ import annotations

from fastapi import APIRouter

from jentic_one import __version__


def make_health_router(surface: str) -> APIRouter:
    """Build a minimal ``/health`` router reporting the given surface name."""
    router = APIRouter()

    @router.get(
        "/health",
        operation_id=f"{surface}Health",
        summary=f"{surface.capitalize()} health",
        tags=["System"],
    )
    async def health() -> dict[str, str]:
        """Return service health status for this surface.

        Unauthenticated liveness probe. In combined mode this is served under
        the surface prefix (e.g. ``/control/health``) so surfaces don't collide;
        the canonical platform probe is the root ``GET /health``.
        """
        return {"status": "ok", "surface": surface, "version": __version__}

    return router
