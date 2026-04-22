"""OpenAPI overlay routes.

Agents contribute OpenAPI overlays to patch the stored spec for an API — fixing
missing auth, correcting base URLs, adding operation metadata, or anything else
the source spec gets wrong or omits.

Overlays start as "pending" and are auto-confirmed on the first successful broker
call that uses them.
"""

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path
from pydantic import Field

from src.db import get_db
from src.openapi_helpers import agent_hints
from src.validators import NormModel


router = APIRouter()

_OVERLAY_FIELD_DESCRIPTION = """\
Full OpenAPI Overlay 1.0 document as a JSON object. Use this to patch the \
stored spec for any API — security schemes, base URL corrections, operation \
metadata, extra extensions, etc.

**Structure:**
```json
{
  "overlay": "1.0.0",
  "info": {"title": "<description>", "version": "1.0.0"},
  "actions": [
    {
      "target": "<JSONPath expression>",
      "update": { }
    }
  ]
}
```

**Common targets:**
- `"$"` — root of the spec (components, info, servers)
- `"$.paths[*][*]"` — all operations (apply global security)
- `"$.paths./foo.get"` — a specific operation

**Security scheme example** (adding BearerAuth to an API):
```json
{
  "overlay": "1.0.0",
  "info": {"title": "GitHub REST auth", "version": "1.0.0"},
  "actions": [
    {
      "target": "$",
      "update": {
        "components": {
          "securitySchemes": {
            "BearerAuth": {"type": "http", "scheme": "bearer"}
          }
        }
      }
    },
    {
      "target": "$.paths[*][*]",
      "update": {"security": [{"BearerAuth": []}]}
    }
  ]
}
```

**Compound apiKey schemes** (e.g. Discourse — two separate apiKey headers): \
name one scheme `Secret` (the primary key) and one `Identity` (the username/ID). \
The broker resolves these by canonical name without needing further annotation.\
"""


# ── Raw overlay endpoint ───────────────────────────────────────────────────


class OverlaySubmit(NormModel):
    """Submit an OpenAPI Overlay 1.0 document to patch an API spec. Commonly used to add missing security schemes."""

    overlay: dict = Field(..., description=_OVERLAY_FIELD_DESCRIPTION)
    contributed_by: str | None = Field(
        default=None,
        description="Optional contributor identifier (username, agent ID, etc.) for tracking overlay source",
    )


@router.post(
    "/apis/{api_id:path}/overlays",
    status_code=201,
    summary="Submit an OpenAPI overlay — patch the stored spec for this API",
    openapi_extra={
        **agent_hints(
            when_to_use="Use when an API's stored OpenAPI spec is missing security schemes, has incorrect base URLs, or lacks required metadata. Submit an OpenAPI Overlay 1.0 document to patch the spec without modifying the original file. Common use: adding BearerAuth or apiKey schemes when the spec declares no security. Overlay starts as pending and auto-confirms on first successful broker call.",
            prerequisites=[
                "Requires authentication (admin/human session)",
                "Valid API ID from GET /apis",
                "Valid OpenAPI Overlay 1.0 structure (overlay, info, actions array)",
            ],
            avoid_when="Do not use for testing security schemes before adding credentials — first add credentials via POST /credentials, then submit overlay if authentication fails with 401/403. Do not submit duplicate overlays — check GET /apis/{api_id}/overlays first.",
            related_operations=[
                "GET /apis/{api_id}/overlays — list existing overlays to avoid duplicates",
                "GET /apis/{api_id} — inspect current security_schemes before patching",
                "POST /credentials — add credentials after overlay is confirmed",
                "GET /apis/{api_id}/openapi.json — download merged spec to verify overlay was applied",
            ],
        ),
        "requestBody": {
            "description": "OpenAPI Overlay 1.0 document to patch the stored spec — adds security schemes, corrects base URLs, or enriches operation metadata"
        },
    },
)
async def submit_overlay(
    api_id: Annotated[str, Path(description="API ID to submit overlay for")],
    body: OverlaySubmit,
):
    """Submit an OpenAPI Overlay 1.0 document to patch the stored spec for this API.

    Overlays are additive and ordered — later overlays override matching keys from
    earlier ones via merge. A new overlay starts as **pending** and is
    auto-confirmed the first time a broker call for this API succeeds.

    See the `overlay` field schema for structure, common targets, and security
    scheme examples including compound apiKey schemes (Discourse-style).
    """
    async with get_db() as db:
        async with db.execute("SELECT id FROM apis WHERE id=?", (api_id,)) as cur:
            api_row = await cur.fetchone()
    if not api_row:
        raise HTTPException(404, f"API '{api_id}' not found.")

    overlay_doc = body.overlay
    if not overlay_doc.get("overlay") or not overlay_doc.get("actions"):
        raise HTTPException(
            422,
            "Invalid overlay: must include 'overlay' (version string) and 'actions' array. "
            "See https://spec.openapis.org/overlay/latest.html",
        )

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
        "_links": {"overlays": f"/apis/{api_id}/overlays", "credentials": "/credentials"},
    }


@router.get(
    "/apis/{api_id:path}/overlays",
    summary="List overlays for an API — returns full overlay documents",
    openapi_extra=agent_hints(
        when_to_use="Use to inspect existing overlays for an API before submitting a new one (avoids duplicates) or to verify which overlays are confirmed vs pending. Each overlay includes the complete OpenAPI Overlay 1.0 document with all actions, so no second call needed. Confirmed overlays are listed first, then pending, ordered by creation date descending.",
        prerequisites=[
            "Requires authentication (toolkit key or human session)",
            "Valid API ID from GET /apis",
        ],
        avoid_when="Do not use to download the merged spec — use GET /apis/{api_id}/openapi.json for that (overlays already applied). Do not use to inspect base security schemes — use GET /apis/{api_id} instead.",
        related_operations=[
            "POST /apis/{api_id}/overlays — submit a new overlay after checking for duplicates",
            "DELETE /apis/{api_id}/overlays/{overlay_id} — delete an overlay",
            "GET /apis/{api_id}/openapi.json — download merged spec with all confirmed overlays applied",
            "GET /apis/{api_id} — view current security_schemes (includes merged overlays)",
        ],
    ),
)
async def list_overlays(api_id: Annotated[str, Path(description="API ID to list overlays for")]):
    """Return all overlays for an API, each with its full overlay document included.

    Confirmed overlays are listed first, then pending, both ordered by creation date
    descending. Each overlay includes the complete OpenAPI Overlay 1.0 document so
    clients don't need a second call to inspect the overlay content.
    """
    async with get_db() as db:
        async with db.execute(
            """SELECT id, overlay, status, contributed_by, confirmed_at, confirmed_by_execution, created_at
               FROM api_overlays WHERE api_id=?
               ORDER BY CASE status WHEN 'confirmed' THEN 0 ELSE 1 END, created_at DESC""",
            (api_id,),
        ) as cur:
            rows = await cur.fetchall()
    return {
        "api_id": api_id,
        "overlays": [
            {
                "id": r[0],
                "overlay": json.loads(r[1]),
                "status": r[2],
                "contributed_by": r[3],
                "confirmed_at": r[4],
                "confirmed_by_execution": r[5],
                "created_at": r[6],
            }
            for r in rows
        ],
    }


@router.delete(
    "/apis/{api_id:path}/overlays/{overlay_id}",
    status_code=200,
    summary="Delete an overlay",
    openapi_extra=agent_hints(
        when_to_use="Use to remove an incorrect or obsolete overlay from an API. Works on both pending and confirmed overlays. After deletion, the merged spec (GET /apis/{api_id}/openapi.json) will no longer include the deleted overlay's patches.",
        prerequisites=[
            "Requires authentication (admin/human session)",
            "Valid API ID and overlay ID from GET /apis/{api_id}/overlays",
        ],
        avoid_when="Do not use to temporarily disable an overlay — deletion is permanent. Do not delete overlays that other toolkits may depend on without coordination.",
        related_operations=[
            "GET /apis/{api_id}/overlays — list overlays to find the overlay_id",
            "POST /apis/{api_id}/overlays — submit a replacement overlay after deleting an incorrect one",
            "GET /apis/{api_id}/openapi.json — verify overlay removal by downloading merged spec",
        ],
    ),
)
async def delete_overlay(
    api_id: Annotated[str, Path(description="API ID")],
    overlay_id: Annotated[str, Path(description="Overlay ID to delete")],
):
    """Delete an overlay by ID.

    Permanently removes the overlay from the database. Works on both pending and confirmed
    overlays. If the overlay was confirmed and actively patching the spec, the next
    broker call will use the spec without this overlay's changes.

    Parameters:
        api_id: API ID that owns this overlay
        overlay_id: Overlay ID to delete (format: overlay_xxxxxxxx)

    Returns:
        Confirmation with deleted overlay_id and api_id.

    Use when an overlay was submitted incorrectly or is no longer needed. To replace
    an incorrect overlay, delete it first, then submit a corrected version.
    """
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM api_overlays WHERE id=? AND api_id=?",
            (overlay_id, api_id),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Overlay not found")
        await db.execute("DELETE FROM api_overlays WHERE id=?", (overlay_id,))
        await db.commit()
    return {"deleted": overlay_id, "api_id": api_id}


async def get_merged_security_schemes(api_id: str) -> dict:
    """Return merged security schemes: native spec + confirmed/pending overlays."""
    schemes = {}

    async with get_db() as db:
        async with db.execute("SELECT spec_path FROM apis WHERE id=?", (api_id,)) as cur:
            row = await cur.fetchone()

    if row and row[0]:
        try:
            with open(row[0]) as f:
                spec = json.load(f)
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

    for overlay_json, _status in overlay_rows:
        try:
            overlay = json.loads(overlay_json)
            for action in overlay.get("actions", []):
                overlay_schemes = (
                    action.get("update", {}).get("components", {}).get("securitySchemes", {})
                )
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
