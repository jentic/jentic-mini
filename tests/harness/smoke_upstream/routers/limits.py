"""Query-array URL-length limits router.

``GET /limits/query-array`` accepts repeated ``?ids=1&ids=2...`` parameters and
echoes them, letting tests push toward the broker's URL-length ceiling
(``414 URI Too Long`` at the gateway/server before code runs). This endpoint
itself imposes no cap; the physical limit is established at the broker boundary.
"""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter
from starlette.requests import Request

router = APIRouter(prefix="/limits", tags=["limits"])

_IDS_PARAM: Final = "ids"


@router.get("/query-array")
async def limits_query_array(request: Request) -> dict[str, object]:
    ids = request.query_params.getlist(_IDS_PARAM)
    return {"count": len(ids), "ids": ids}
