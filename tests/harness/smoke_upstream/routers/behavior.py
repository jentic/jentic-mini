"""Echo router — reflects exactly how a request arrived at the upstream.

Test runners assert against the returned :class:`RequestEcho` to verify the
broker forwarded headers, query parameters, the client IP, and the body without
mutation (e.g. that an injected credential header arrived intact).
"""

from __future__ import annotations

import base64
import uuid
from typing import Final

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/behavior", tags=["behavior"])

HEADER_ASYNC_ORIGIN: Final = "Jentic-Async-Origin"


class RequestEcho(BaseModel):
    method: str
    url_path: str
    headers: dict[str, str]
    query_params: dict[str, str]
    client_ip: str
    body_base64: str | None = None
    body_text: str | None = None


@router.post("/echo")
async def echo(request: Request) -> RequestEcho:
    raw = await request.body()
    body_text: str | None = None
    body_base64: str | None = None
    if raw:
        try:
            body_text = raw.decode("utf-8")
        except UnicodeDecodeError:
            body_base64 = base64.b64encode(raw).decode("ascii")

    client_ip = request.client.host if request.client is not None else ""

    return RequestEcho(
        method=request.method,
        url_path=request.url.path,
        headers=dict(request.headers),
        query_params=dict(request.query_params),
        client_ip=client_ip,
        body_base64=body_base64,
        body_text=body_text,
    )


@router.post("/upstream-async")
async def upstream_async(request: Request) -> JSONResponse:
    body: dict[str, object] = {"job_id": str(uuid.uuid4()), "origin": "upstream"}
    headers: dict[str, str] = {}
    async_origin = request.headers.get(HEADER_ASYNC_ORIGIN)
    if async_origin is not None:
        body["async_origin"] = async_origin
        headers[HEADER_ASYNC_ORIGIN] = async_origin
    return JSONResponse(status_code=202, content=body, headers=headers)
