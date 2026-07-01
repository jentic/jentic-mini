"""Deprecation / lifecycle-header router (RFC 8594).

``GET /lifecycle/deprecated-endpoint`` returns the upstream's OWN ``Deprecation``
and ``Sunset`` headers. Scope note: these are the upstream's headers, passed
through verbatim by the broker. The broker must NOT add a bare ``Warning: 299``
(only ``Jentic-*`` headers are broker-added, B-002); harvesting these signals
into a Note is a broker-side self-healing sidecar concern, out of scope here.
"""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])

HEADER_DEPRECATION: Final = "Deprecation"
HEADER_SUNSET: Final = "Sunset"

_DEPRECATION_VALUE: Final = "true"
_SUNSET_DATE: Final = "Wed, 11 Nov 2026 23:59:59 GMT"


@router.get("/deprecated-endpoint")
async def lifecycle_deprecated_endpoint() -> JSONResponse:
    headers = {HEADER_DEPRECATION: _DEPRECATION_VALUE, HEADER_SUNSET: _SUNSET_DATE}
    return JSONResponse(content={"ok": True}, headers=headers)
