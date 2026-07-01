"""Spec-vs-reality drift router.

Each endpoint intentionally contradicts what its OpenAPI spec would declare, so
tests can assert the broker passes undocumented status codes, content types, and
schemas through without crashing. The async validation sidecar (broker-side, out
of scope here) is what later notices the drift.
"""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter
from starlette.responses import JSONResponse, PlainTextResponse

router = APIRouter(prefix="/drift", tags=["drift"])

_TEAPOT_STATUS: Final = 418


@router.get("/status-code")
async def drift_status_code() -> JSONResponse:
    return JSONResponse(status_code=_TEAPOT_STATUS, content={"detail": "I'm a teapot"})


@router.get("/content-type")
async def drift_content_type() -> PlainTextResponse:
    return PlainTextResponse(content="plain text where JSON was declared")


@router.get("/schema")
async def drift_schema() -> dict[str, object]:
    return {"foo": "bar"}
