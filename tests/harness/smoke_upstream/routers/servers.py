"""Templated-server / base-URL resolution echo router.

``GET /servers/resolution`` echoes the host and path the request arrived with.
The real assertion is **broker-side**: the broker resolves OpenAPI templated
``servers`` (e.g. ``https://{tenant}.api.vendor.com/{version}``) and matches the
forwarded URL back to the stored operation. This endpoint just confirms what
ultimately reached the upstream.
"""

from __future__ import annotations

from fastapi import APIRouter
from starlette.requests import Request

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("/resolution")
async def servers_resolution(request: Request) -> dict[str, object]:
    return {
        "host": request.url.hostname,
        "path": request.url.path,
        "resolved": True,
    }
