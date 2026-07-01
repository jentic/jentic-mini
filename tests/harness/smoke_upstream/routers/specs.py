"""Multi-version and poisoned OpenAPI spec hosting router.

Serves specs of several OpenAPI/Swagger versions plus intentionally malicious
payloads so Registry ingestion can be tested for version handling, graceful
rejection, forward-compatibility, and parser-bomb resilience. Hand-built docs
keep this independent of FastAPI's own generated schema and any import cycles.
"""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter
from starlette.responses import PlainTextResponse

router = APIRouter(prefix="/specs", tags=["specs"])

OPENAPI_31_VERSION: Final = "3.1.0"
OPENAPI_30_VERSION: Final = "3.0.3"
SWAGGER_20_VERSION: Final = "2.0"
FUTURE_40_VERSION: Final = "4.0.0"

MEDIA_TYPE_YAML: Final = "application/yaml"
MEDIA_TYPE_XML: Final = "text/xml"

# Kept well under any production "50MB monolith" ceiling (a Mode-2, networked
# concern) so the in-memory suite stays fast while still being non-trivial.
_MASSIVE_ENTRY_COUNT: Final = 3000

_INFO: Final = {"title": "Smoke Upstream", "version": "1.0.0"}


def _minimal_paths() -> dict[str, object]:
    return {
        "/ping": {
            "get": {
                "operationId": "ping",
                "responses": {"200": {"description": "ok"}},
            }
        }
    }


@router.get("/openapi-3.1.json")
async def specs_openapi_31() -> dict[str, object]:
    return {
        "openapi": OPENAPI_31_VERSION,
        "info": _INFO,
        "paths": _minimal_paths(),
        "webhooks": {
            "newItem": {
                "post": {"responses": {"200": {"description": "ack"}}},
            }
        },
        "components": {
            "schemas": {
                "Item": {
                    "type": "object",
                    "properties": {"count": {"type": "integer", "exclusiveMinimum": 0}},
                }
            }
        },
    }


@router.get("/openapi-3.0.json")
async def specs_openapi_30() -> dict[str, object]:
    return {
        "openapi": OPENAPI_30_VERSION,
        "info": _INFO,
        "paths": _minimal_paths(),
        "components": {
            "schemas": {
                "Item": {
                    "type": "object",
                    "properties": {"name": {"type": "string", "nullable": True}},
                }
            }
        },
    }


@router.get("/swagger-2.0.json")
async def specs_swagger_20() -> dict[str, object]:
    return {
        "swagger": SWAGGER_20_VERSION,
        "info": _INFO,
        "paths": {"/ping": {"get": {"responses": {"200": {"description": "ok"}}}}},
    }


@router.get("/future-4.0.json")
async def specs_future_40() -> dict[str, object]:
    return {
        "openapi": FUTURE_40_VERSION,
        "info": _INFO,
        "paths": _minimal_paths(),
        "x-unknown-future-field": {"speculative": True},
        "dimensions": ["time", "space"],
    }


_INFINITE_LOOP_YAML: Final = """openapi: "3.1.0"
info:
  title: Poisoned Spec
  version: "1.0.0"
paths: {}
components:
  schemas:
    SchemaA:
      $ref: "#/components/schemas/SchemaB"
    SchemaB:
      $ref: "#/components/schemas/SchemaA"
"""


@router.get("/poison/infinite-loop.yaml")
async def specs_poison_infinite_loop() -> PlainTextResponse:
    return PlainTextResponse(content=_INFINITE_LOOP_YAML, media_type=MEDIA_TYPE_YAML)


_BILLION_LAUGHS_XML: Final = """<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<lolz>&lol3;</lolz>
"""


@router.get("/poison/billion-laughs.xml")
async def specs_poison_billion_laughs() -> PlainTextResponse:
    return PlainTextResponse(content=_BILLION_LAUGHS_XML, media_type=MEDIA_TYPE_XML)


@router.get("/poison/massive.json")
async def specs_poison_massive() -> dict[str, object]:
    schemas: dict[str, object] = {
        f"Entity{index}": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "ref": {"$ref": f"#/components/schemas/Entity{index}"},
            },
        }
        for index in range(_MASSIVE_ENTRY_COUNT)
    }
    return {
        "openapi": OPENAPI_31_VERSION,
        "info": _INFO,
        "paths": _minimal_paths(),
        "components": {"schemas": schemas},
    }
