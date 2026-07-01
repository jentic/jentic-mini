"""OpenAPI parameter-serialization echo router.

Tests OpenAPI ``style``/``explode`` rules (matrix, pipeDelimited, deepObject,
comma-separated header arrays). The broker forwards these untouched; the
Registry's ingestion and the agent's tool-calling loop must generate them
correctly. Each endpoint parses the inbound serialization and echoes the parsed
value so a test can assert the wire format survived the round trip.
"""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter
from starlette.requests import Request

router = APIRouter(prefix="/parameters", tags=["parameters"])

HEADER_ARRAY: Final = "X-Array"

_PIPE_DELIMITER: Final = "|"
_DEEP_OBJECT_PREFIX: Final = "user["
_DEEP_OBJECT_SUFFIX: Final = "]"
_MATRIX_SEGMENT_PREFIX: Final = ";"
_MATRIX_PAIR_SEP: Final = "="


def _parse_matrix(segment: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for pair in segment.split(_MATRIX_SEGMENT_PREFIX):
        if _MATRIX_PAIR_SEP not in pair:
            continue
        key, value = pair.split(_MATRIX_PAIR_SEP, 1)
        if key:
            parsed[key] = value
    return parsed


@router.get("/query/matrix/{segment:path}")
async def parameters_matrix(segment: str) -> dict[str, object]:
    return {"parsed": _parse_matrix(segment)}


@router.get("/query/pipe")
async def parameters_pipe(request: Request) -> dict[str, object]:
    raw = request.query_params.get("array", "")
    values = raw.split(_PIPE_DELIMITER) if raw else []
    return {"array": values}


@router.get("/query/deep-object")
async def parameters_deep_object(request: Request) -> dict[str, object]:
    user: dict[str, str] = {}
    for key, value in request.query_params.multi_items():
        if key.startswith(_DEEP_OBJECT_PREFIX) and key.endswith(_DEEP_OBJECT_SUFFIX):
            inner = key[len(_DEEP_OBJECT_PREFIX) : -len(_DEEP_OBJECT_SUFFIX)]
            if inner:
                user[inner] = value
    return {"user": user}


@router.get("/header/array")
async def parameters_header_array(request: Request) -> dict[str, object]:
    raw = request.headers.get(HEADER_ARRAY, "")
    values = [item.strip() for item in raw.split(",") if item.strip()] if raw else []
    return {"values": values}
