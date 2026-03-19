"""OpenAPI overlay routes.

Agents contribute security scheme information for APIs that don't define auth
in their OpenAPI spec. Two paths:

1. **Structured (recommended):** `POST /apis/{api_id}/scheme` — describe the
   scheme type in simple terms; Jentic generates the overlay internally.

2. **Raw overlay:** `POST /apis/{api_id}/overlays` — supply a full OpenAPI
   Overlay 1.0 document for anything exotic.

Once a broker call succeeds using the scheme, the overlay is auto-confirmed and
permanently merged into all future spec serves for that API.
"""
import json
import uuid
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.db import get_db

router = APIRouter()


# ── Structured scheme input ──────────────────────────────────────────────────

class SchemeInput(BaseModel):
    """Structured description of an API's authentication scheme.

    Jentic generates the OpenAPI overlay from this; no need to write overlay YAML.
    Multiple entries can be submitted in one call for APIs requiring more than
    one header (e.g. Discourse needs Api-Key + Api-Username).
    """
    type: Literal["apiKey", "bearer", "basic", "oauth2_client_credentials", "openIdConnect"]
    """Authentication type. Use 'apiKey' for header/query/cookie keys, 'bearer' for
    Authorization: Bearer tokens, 'basic' for HTTP Basic, 'oauth2_client_credentials'
    for machine-to-machine OAuth2, 'openIdConnect' for OIDC discovery."""

    # apiKey params
    location: Literal["header", "query", "cookie"] | None = Field(None, alias="in")
    """Where the key is sent. Required when type='apiKey'. Usually 'header'."""
    name: str | None = None
    """Header/query/cookie name carrying the key. Required when type='apiKey'.
    Examples: 'Api-Key', 'X-API-Key', 'Authorization', 'api_key'."""

    # OAuth2 params
    token_url: str | None = None
    """Token endpoint URL. Required when type='oauth2_client_credentials'."""

    # OpenIdConnect params
    openid_connect_url: str | None = None
    """Discovery document URL. Required when type='openIdConnect'."""

    scheme_name: str | None = None
    """Name for this scheme in the overlay. Auto-derived if omitted.
    e.g. 'ApiKeyAuth', 'BearerAuth'. Use this value in scheme_name when
    calling POST /credentials."""

    contributed_by: str | None = None

    class Config:
        populate_by_name = True


def _generate_overlay(api_id: str, schemes: list[SchemeInput]) -> tuple[dict, list[str]]:
    """Generate an OpenAPI Overlay 1.0 document from structured scheme inputs.
    Returns (overlay_doc, list_of_scheme_names)."""
    security_schemes = {}
    security_req = {}

    for s in schemes:
        # Derive scheme_name if not provided
        if s.scheme_name:
            name = s.scheme_name
        elif s.type == "apiKey":
            loc = s.location or "header"
            raw = (s.name or "X-API-Key").replace("-", "").replace("_", "")
            name = f"{raw}Auth" if not raw.endswith("Auth") else raw
        elif s.type == "bearer":
            name = "BearerAuth"
        elif s.type == "basic":
            name = "BasicAuth"
        elif s.type == "oauth2_client_credentials":
            name = "OAuth2ClientCredentials"
        elif s.type == "openIdConnect":
            name = "OpenIdConnect"
        else:
            name = "Auth"

        if s.type == "apiKey":
            loc = s.location or "header"
            security_schemes[name] = {
                "type": "apiKey",
                "in": loc,
                "name": s.name or "X-API-Key",
            }
        elif s.type == "bearer":
            security_schemes[name] = {"type": "http", "scheme": "bearer"}
        elif s.type == "basic":
            security_schemes[name] = {"type": "http", "scheme": "basic"}
        elif s.type == "oauth2_client_credentials":
            if not s.token_url:
                raise ValueError("token_url is required for oauth2_client_credentials")
            security_schemes[name] = {
                "type": "oauth2",
                "flows": {
                    "clientCredentials": {
                        "tokenUrl": s.token_url,
                        "scopes": {},
                    }
                },
            }
        elif s.type == "openIdConnect":
            if not s.openid_connect_url:
                raise ValueError("openid_connect_url is required for openIdConnect")
            security_schemes[name] = {
                "type": "openIdConnect",
                "openIdConnectUrl": s.openid_connect_url,
            }

        security_req[name] = []

    overlay = {
        "overlay": "1.0.0",
        "info": {"title": f"Auth overlay for {api_id}", "version": "1.0.0"},
        "actions": [
            {
                "target": "$",
                "update": {"components": {"securitySchemes": security_schemes}},
            },
            {
                "target": "$.paths[*][*]",
                "update": {"security": [security_req]},
            },
        ],
    }
    return overlay, list(security_schemes.keys())


# ── Structured scheme endpoint ─────────────────────────────────────────────

@router.post("/apis/{api_id:path}/scheme", status_code=201, summary="Declare auth scheme — teach Jentic how to authenticate with this API")
async def submit_scheme(api_id: str, body: SchemeInput | list[SchemeInput]):
    """Registers a security scheme for an API that has missing or incorrect auth in its spec.
    Generates an OpenAPI overlay stored as pending; auto-confirmed when broker gets a 2xx.
    Supports: apiKey (header/query/cookie), bearer token, HTTP basic, OAuth2 client credentials, multiple headers.
    Returns generated_overlay, scheme_names, and next_steps for credential registration.
    Use this when the broker returns 'no security scheme found' for an API.
    """
    async with get_db() as db:
        async with db.execute("SELECT id FROM apis WHERE id=?", (api_id,)) as cur:
            api_row = await cur.fetchone()
    if not api_row:
        raise HTTPException(404, f"API '{api_id}' not found. Register it first via POST /apis.")

    # Check if a confirmed overlay already exists
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM api_overlays WHERE api_id=? AND status='confirmed' LIMIT 1",
            (api_id,),
        ) as cur:
            existing = await cur.fetchone()
    if existing:
        return {
            "message": f"A confirmed security scheme is already on record for '{api_id}'. "
                       f"You can proceed to POST /credentials.",
            "existing_overlay_id": existing[0],
            "status": "already_confirmed",
        }

    schemes = body if isinstance(body, list) else [body]
    contributed_by = schemes[0].contributed_by if schemes else None

    try:
        overlay_doc, scheme_names = _generate_overlay(api_id, schemes)
    except ValueError as e:
        raise HTTPException(422, str(e))

    oid = str(uuid.uuid4())
    async with get_db() as db:
        await db.execute(
            "INSERT INTO api_overlays (id, api_id, overlay, status, contributed_by) VALUES (?,?,?,'pending',?)",
            (oid, api_id, json.dumps(overlay_doc), contributed_by),
        )
        await db.commit()

    return {
        "id": oid,
        "api_id": api_id,
        "status": "pending",
        "scheme_names": scheme_names,
        "generated_overlay": overlay_doc,
        "message": (
            f"Security scheme registered for '{api_id}'. "
            f"It will be auto-confirmed the first time a broker call succeeds. "
            f"Use the scheme_name(s) below when calling POST /credentials."
        ),
        "next_steps": [
            {
                "step": 1,
                "action": "POST /credentials",
                "note": f"Add your credential(s) for '{api_id}', setting api_id='{api_id}' "
                        f"and scheme_name to one of: {scheme_names}",
            },
            {
                "step": 2,
                "action": f"GET /{api_id}/...",
                "note": "Make any API call via the broker. On first success, the scheme is permanently confirmed.",
            },
        ],
        "_links": {
            "self": f"/apis/{api_id}/overlays/{oid}",
            "credentials": "/credentials",
        },
    }


# ── Raw overlay endpoint (power users / exotic schemes) ────────────────────

class OverlaySubmit(BaseModel):
    overlay: dict
    """Full OpenAPI Overlay 1.0 document as a JSON object."""
    contributed_by: str | None = None


@router.post("/apis/{api_id:path}/overlays", status_code=201, summary="Submit raw OpenAPI overlay — patch the spec directly")
async def submit_overlay(api_id: str, body: OverlaySubmit):
    """Submit a raw OpenAPI overlay JSON to patch the stored spec for this API. Stored as pending; auto-confirmed on first successful broker call. Prefer POST /apis/{api_id}/scheme for structured auth registration."""
    async with get_db() as db:
        async with db.execute("SELECT id FROM apis WHERE id=?", (api_id,)) as cur:
            api_row = await cur.fetchone()
    if not api_row:
        raise HTTPException(404, f"API '{api_id}' not found.")

    overlay_doc = body.overlay
    if not overlay_doc.get("overlay") or not overlay_doc.get("actions"):
        raise HTTPException(
            422,
            "Invalid overlay: must include 'overlay' (version) and 'actions' array. "
            "See https://spec.openapis.org/overlay/latest.html",
        )

    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM api_overlays WHERE api_id=? AND status='confirmed' LIMIT 1",
            (api_id,),
        ) as cur:
            existing = await cur.fetchone()
    if existing:
        return {
            "message": f"A confirmed overlay already exists for '{api_id}'.",
            "existing_overlay_id": existing[0],
            "status": "already_confirmed",
        }

    oid = str(uuid.uuid4())
    async with get_db() as db:
        await db.execute(
            "INSERT INTO api_overlays (id, api_id, overlay, status, contributed_by) VALUES (?,?,?,'pending',?)",
            (oid, api_id, json.dumps(overlay_doc), body.contributed_by),
        )
        await db.commit()

    return {
        "id": oid,
        "api_id": api_id,
        "status": "pending",
        "message": f"Overlay submitted for '{api_id}'. Auto-confirmed on first successful broker call.",
        "_links": {"self": f"/apis/{api_id}/overlays/{oid}", "credentials": "/credentials"},
    }


@router.get("/apis/{api_id:path}/overlays", summary="List overlays for an API")
async def list_overlays(api_id: str):
    """List all overlays for an API."""
    async with get_db() as db:
        async with db.execute(
            """SELECT id, status, contributed_by, confirmed_at, created_at
               FROM api_overlays WHERE api_id=?
               ORDER BY CASE status WHEN 'confirmed' THEN 0 ELSE 1 END, created_at DESC""",
            (api_id,),
        ) as cur:
            rows = await cur.fetchall()
    return {
        "api_id": api_id,
        "overlays": [
            {"id": r[0], "status": r[1], "contributed_by": r[2], "confirmed_at": r[3], "created_at": r[4]}
            for r in rows
        ],
    }


@router.get("/apis/{api_id:path}/overlays/{overlay_id}")
async def get_overlay(api_id: str, overlay_id: str):
    """Get a specific overlay including its full document."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, overlay, status, contributed_by, confirmed_at, confirmed_by_execution, created_at FROM api_overlays WHERE id=? AND api_id=?",
            (overlay_id, api_id),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Overlay not found")
    return {
        "id": row[0], "api_id": api_id, "overlay": json.loads(row[1]),
        "status": row[2], "contributed_by": row[3], "confirmed_at": row[4],
        "confirmed_by_execution": row[5], "created_at": row[6],
    }


async def get_merged_security_schemes(api_id: str) -> dict:
    """Return merged security schemes: native spec + confirmed/pending overlays."""
    import json as _json
    schemes = {}

    async with get_db() as db:
        async with db.execute("SELECT spec_path FROM apis WHERE id=?", (api_id,)) as cur:
            row = await cur.fetchone()

    if row and row[0]:
        try:
            with open(row[0]) as f:
                spec = _json.load(f)
            spec_schemes = spec.get("components", {}).get("securitySchemes", {})
            global_security = spec.get("security", [])
            if global_security:
                schemes.update(spec_schemes)
        except Exception:
            pass

    async with get_db() as db:
        async with db.execute(
            "SELECT overlay, status FROM api_overlays WHERE api_id=? ORDER BY CASE status WHEN 'confirmed' THEN 0 ELSE 1 END, created_at ASC",
            (api_id,),
        ) as cur:
            overlay_rows = await cur.fetchall()

    for (overlay_json, _status) in overlay_rows:
        try:
            overlay = _json.loads(overlay_json)
            for action in overlay.get("actions", []):
                overlay_schemes = action.get("update", {}).get("components", {}).get("securitySchemes", {})
                schemes.update(overlay_schemes)
        except Exception:
            pass

    return schemes


async def confirm_overlay(api_id: str, execution_id: str) -> None:
    """Mark the first pending overlay for an API as confirmed."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM api_overlays WHERE api_id=? AND status='pending' ORDER BY created_at ASC LIMIT 1",
            (api_id,),
        ) as cur:
            row = await cur.fetchone()
        if row:
            await db.execute(
                "UPDATE api_overlays SET status='confirmed', confirmed_at=unixepoch(), confirmed_by_execution=? WHERE id=?",
                (execution_id, row[0]),
            )
            await db.commit()
