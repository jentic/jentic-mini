"""OpenAPI overlay routes.

Agents contribute OpenAPI overlays to patch the stored spec for an API — fixing
missing auth, correcting base URLs, adding operation metadata, or anything else
the source spec gets wrong or omits.

Overlays start as "pending" and are auto-confirmed on the first successful broker
call that uses them.
"""
import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import Field
from src.validators import NormModel
from src.db import get_db

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
    overlay: dict = Field(..., description=_OVERLAY_FIELD_DESCRIPTION)
    contributed_by: str | None = None


@router.post(
    "/apis/{api_id:path}/overlays",
    status_code=201,
    summary="Submit an OpenAPI overlay — patch the stored spec for this API",
)
async def submit_overlay(api_id: str, body: OverlaySubmit):
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


@router.get("/apis/{api_id:path}/overlays", summary="List overlays for an API — returns full overlay documents")
async def list_overlays(api_id: str):
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


@router.delete("/apis/{api_id:path}/overlays/{overlay_id}", status_code=200, summary="Delete an overlay")
async def delete_overlay(api_id: str, overlay_id: str):
    """Delete an overlay by ID. Works on both pending and confirmed overlays."""
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
