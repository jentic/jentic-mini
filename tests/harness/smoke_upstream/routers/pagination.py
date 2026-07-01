"""Deterministic pagination router for testing agent-loop logic.

Exposes cursor, RFC 8288 ``Link``-header, and offset pagination over a fixed
finite dataset so an agent's paging behaviour can be asserted end-to-end. The
broker forwards these untouched (the opt-in ``response.rewrite_navigation``
processor that rewrites ``Link`` targets is a broker-side concern, out of scope
here).
"""

from __future__ import annotations

import base64
from typing import Final

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/pagination", tags=["pagination"])

TOTAL_ITEMS: Final = 25
DEFAULT_PAGE_SIZE: Final = 10

HEADER_LINK: Final = "Link"

_LINK_REL_NEXT: Final = 'rel="next"'


def _item(index: int) -> dict[str, object]:
    return {"id": index, "name": f"item-{index}"}


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return int(base64.urlsafe_b64decode(cursor.encode("ascii")).decode("ascii"))
    except (ValueError, UnicodeDecodeError):
        return 0


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode("ascii")).decode("ascii")


@router.get("/cursor")
async def pagination_cursor(request: Request) -> dict[str, object]:
    offset = _decode_cursor(request.query_params.get("cursor"))
    end = min(offset + DEFAULT_PAGE_SIZE, TOTAL_ITEMS)
    data = [_item(index) for index in range(offset, end)]
    next_cursor = _encode_cursor(end) if end < TOTAL_ITEMS else None
    return {"data": data, "next_cursor": next_cursor}


@router.get("/links")
async def pagination_links(request: Request) -> JSONResponse:
    try:
        page = max(1, int(request.query_params.get("page", "1")))
    except ValueError:
        page = 1
    start = (page - 1) * DEFAULT_PAGE_SIZE
    end = min(start + DEFAULT_PAGE_SIZE, TOTAL_ITEMS)
    data = [_item(index) for index in range(start, end)]

    headers: dict[str, str] = {}
    if end < TOTAL_ITEMS:
        next_url = f"{request.url.path}?page={page + 1}"
        headers[HEADER_LINK] = f"<{next_url}>; {_LINK_REL_NEXT}"
    return JSONResponse(content={"data": data}, headers=headers)


@router.get("/offset")
async def pagination_offset(request: Request) -> dict[str, object]:
    try:
        limit = int(request.query_params.get("limit", str(DEFAULT_PAGE_SIZE)))
        offset = int(request.query_params.get("offset", "0"))
    except ValueError:
        limit, offset = DEFAULT_PAGE_SIZE, 0
    limit = max(0, limit)
    offset = max(0, offset)
    data = [_item(index) for index in range(offset, min(offset + limit, TOTAL_ITEMS))]
    return {"data": data, "total": TOTAL_ITEMS}
