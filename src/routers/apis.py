"""API registry routes — add, list, and index operations."""
import re
import uuid
import json
import yaml
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from src.models import ApiRegister, ApiOut, OperationOut, ApiListPage, OperationListPage
from src.db import get_db
import src.bm25 as bm25

router = APIRouter()


def _extract_vendor(api_id: str | None) -> str | None:
    """Extract registrable domain from a URL-derived API ID.

    Examples:
        travelpartner.googleapis.com  -> googleapis.com
        api.stripe.com                -> stripe.com
        api.zoom.us/v2                -> zoom.us
        api.elevenlabs.io             -> elevenlabs.io
    """
    if not api_id:
        return None
    hostname = api_id.split("/")[0]   # strip any path component
    parts = hostname.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return hostname or None


# ── helpers ───────────────────────────────────────────────────────────────────

def _extract_base_url(doc: dict) -> str | None:
    """
    Extract the canonical base URL from an OpenAPI spec's servers array.
    Returns the first server URL, stripping trailing slash.
    e.g. "https://api.elevenlabs.io" from servers[0].url = "https://api.elevenlabs.io"
    """
    servers = doc.get("servers", [])
    if servers and isinstance(servers, list):
        url = servers[0].get("url", "").rstrip("/")
        if url.startswith("http"):
            return url
        return url if url else None
    return None


def _strip_version_suffix(path: str) -> str:
    """Strip a trailing version segment from a URL path.

    Matches:
      /v1, /v2, /v10         (vN)
      /1.0, /3.0, /2023-01   (major.minor or date-like)
      /1                     (bare integer, only at end)

    Does NOT strip structural path components like /api, /rest, etc.

    Examples:
      /v1           → ''
      /api/v10      → /api
      /api/1.0      → /api
      /api          → /api   (unchanged — not a version)
    """
    return re.sub(r"(/v\d+(\.\d+)*|/\d{4}-\d{2}-\d{2}|/\d+\.\d+|/\d+)$", "", path)


def _derive_api_id(base_url: str) -> str:
    """
    Derive an API ID from its base URL.

    Strips the URL scheme and trailing version segments so the ID identifies
    the service, not a particular version of it:
      https://api.openai.com/v1   → api.openai.com
      https://api.zoom.us/v2      → api.zoom.us
      https://discord.com/api/v10 → discord.com/api
      https://api.stripe.com      → api.stripe.com  (no change)

    Template variables are also removed:
      https://{dc}.api.mailchimp.com/3.0  → api.mailchimp.com
      https://{your-domain}.atlassian.net → atlassian.net
    """
    parsed = urlparse(base_url)
    host = parsed.hostname or parsed.netloc or ""
    path = parsed.path.rstrip("/")

    # Strip path segments containing template vars entirely
    if path:
        clean_segments = [s for s in path.split("/") if "{" not in s and s]
        path = "/" + "/".join(clean_segments) if clean_segments else ""

    # Strip trailing version suffix
    path = _strip_version_suffix(path)

    # Strip template vars from hostname (e.g. {dc}.api.mailchimp.com → api.mailchimp.com)
    host = re.sub(r"\{[^}]+\}\.", "", host)   # leading template labels
    host = re.sub(r"\.\{[^}]+\}", "", host)   # trailing template labels
    host = host.strip(".")

    return (host + path).lower() if host else base_url


def _compute_jentic_id(method: str, base_url: str | None, path: str) -> str:
    """
    Compute the canonical capability id for an operation.

    Format: "METHOD/host/path"  (scheme omitted — always https; single slash separator)
    e.g.:   "GET/api.elevenlabs.io/v1/models"
            "POST/api.stripe.com/v1/payment_intents"

    The method is always a valid HTTP verb; a hostname can never start with one,
    so METHOD/host/path is unambiguous without any special separator.

    If base_url is unavailable, falls back to:
            "GET/path"  (relative — still unambiguous within the API)
    """
    if base_url:
        host = re.sub(r"^https?://", "", base_url).rstrip("/")
        if not path.startswith("/"):
            path = "/" + path
        return f"{method.upper()}/{host}{path}"
    return f"{method.upper()}/{path}"


def _parse_operations(api_id: str, spec_path: str, base_url: str | None = None) -> list[dict]:
    """
    Extract operations from an OpenAPI spec file.

    Returns a list of operation dicts with:
    - id: UUID (internal DB key)
    - jentic_id: "METHOD https://host/path" (the public semantic identifier)
    - operation_id: OpenAPI operationId string
    - method, path, summary, description
    """
    p = Path(spec_path)
    if not p.exists():
        return []
    raw = p.read_text()
    doc = yaml.safe_load(raw) if spec_path.endswith((".yaml", ".yml")) else json.loads(raw)

    # Use passed base_url or extract from spec
    resolved_base = base_url or _extract_base_url(doc)

    ops = []
    for path, methods in doc.get("paths", {}).items():
        for method, op in methods.items():
            if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
                continue
            jentic_id = _compute_jentic_id(method, resolved_base, path)
            ops.append({
                "id": str(uuid.uuid4()),
                "api_id": api_id,
                "operation_id": op.get("operationId"),
                "jentic_id": jentic_id,
                "method": method.upper(),
                "path": path,
                "summary": op.get("summary", ""),
                "description": op.get("description", ""),
            })
    return ops


def _load_base_url_from_spec(spec_path: str) -> str | None:
    """Load and extract base URL from a spec file."""
    p = Path(spec_path)
    if not p.exists():
        return None
    try:
        raw = p.read_text()
        doc = yaml.safe_load(raw) if spec_path.endswith((".yaml", ".yml")) else json.loads(raw)
        return _extract_base_url(doc)
    except Exception:
        return None


async def _rebuild_index():
    """Rebuild BM25 index from all operations + workflows in DB.

    BM25 is CPU-bound; runs in a thread pool so it doesn't block the event loop.
    """
    import asyncio
    import json as _json
    async with get_db() as db:
        async with db.execute(
            """SELECT o.id, o.api_id, o.operation_id, o.jentic_id, o.method, o.path,
                      o.summary, o.description, a.id as api_url_id
               FROM operations o
               LEFT JOIN apis a ON o.api_id = a.id"""
        ) as cur:
            op_rows = await cur.fetchall()
        async with db.execute(
            "SELECT slug, name, description, involved_apis FROM workflows"
        ) as cur:
            wf_rows = await cur.fetchall()

    ops = [
        {
            "_id": r[0],
            "_operation_id": r[2],
            "_api_id": r[1],           # raw api_id for _links construction
            "id": r[3],
            "summary": r[6],
            "description": r[7],
            "_vendor": _extract_vendor(r[8]),
        }
        for r in op_rows
    ]

    # Import here to avoid circular import at module load time
    try:
        from src.routers.workflows import workflow_capability_id
    except Exception:
        workflow_capability_id = lambda s: f"POST/jentic-mini.home.seanblanchfield.com/workflows/{s}"  # TODO: import JENTIC_HOSTNAME

    wfs = [
        {
            "id": workflow_capability_id(r[0]),
            "slug": r[0],
            "name": r[1],
            "summary": r[1],
            "description": r[2],
            "involved_apis": _json.loads(r[3]) if r[3] else [],
        }
        for r in wf_rows
    ]

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, bm25.build, ops, wfs)



def _row_to_op(r) -> dict:
    """Map a DB row to the public OperationOut shape.

    Row order: id, api_id, operation_id, jentic_id, method, path, summary, description
    DB jentic_id → public id. Description is abbreviated for token efficiency.
    """
    from src.utils import abbreviate
    return {
        "id": r[3],
        "summary": r[6],
        "description": abbreviate(r[7]),
    }


# ── routes ────────────────────────────────────────────────────────────────────

@router.post("/apis", response_model=ApiOut, status_code=201, summary="Add API", include_in_schema=False, deprecated=True)
async def add_api(body: ApiRegister):
    # Extract base URL from spec
    base_url = _load_base_url_from_spec(body.spec_path) if body.spec_path else None

    # Derive canonical API ID from base URL; fall back to caller-provided id
    api_id = body.id
    if not api_id:
        if base_url:
            api_id = _derive_api_id(base_url)
        else:
            raise HTTPException(400, "Cannot derive API id: no base_url in spec and no id provided")

    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO apis (id, name, description, spec_path, base_url) VALUES (?,?,?,?,?)",
            (api_id, body.name, body.description, body.spec_path, base_url),
        )
        await db.execute("DELETE FROM operations WHERE api_id=?", (api_id,))
        ops = _parse_operations(api_id, body.spec_path, base_url)
        for op in ops:
            await db.execute(
                """INSERT INTO operations
                   (id, api_id, operation_id, jentic_id, method, path, summary, description)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (op["id"], op["api_id"], op["operation_id"], op["jentic_id"],
                 op["method"], op["path"], op["summary"], op["description"]),
            )
        await db.commit()
        async with db.execute(
            "SELECT id, name, description, spec_path, base_url, created_at FROM apis WHERE id=?",
            (api_id,)
        ) as cur:
            row = await cur.fetchone()

    await _rebuild_index()
    return {"id": row[0], "name": row[1], "vendor": _extract_vendor(row[0]),
            "description": row[2], "spec_path": row[3], "base_url": row[4], "created_at": row[5]}


@router.get("/apis", summary="List registered APIs — browse available API providers", response_model=ApiListPage)
async def list_apis(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
):
    """Returns paginated list of registered API providers with id, name, vendor, and operation count."""
    offset = (page - 1) * limit
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM apis") as cur:
            total = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT id, name, description, spec_path, base_url, created_at FROM apis ORDER BY id LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cur:
            rows = await cur.fetchall()

    total_pages = max(1, (total + limit - 1) // limit)
    has_more = page < total_pages
    return {
        "data": [{"id": r[0], "name": r[1], "vendor": _extract_vendor(r[0]),
                  "description": r[2], "spec_path": r[3], "base_url": r[4], "created_at": r[5]}
                 for r in rows],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "has_more": has_more,
        "_links": {
            "self": f"/apis?page={page}&limit={limit}",
            **({"next": f"/apis?page={page + 1}&limit={limit}"} if has_more else {}),
            **({"prev": f"/apis?page={page - 1}&limit={limit}"} if page > 1 else {}),
        },
    }


@router.get("/apis/{api_id:path}/operations", summary="List operations for an API — enumerate all available actions", response_model=OperationListPage)
async def list_api_operations(
    api_id: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(50, ge=1, le=200, description="Results per page"),
):
    """Returns paginated list of operations for the given API. Each item has capability id, summary, and description. Use GET /inspect/{id} for full schema."""
    offset = (page - 1) * limit
    async with get_db() as db:
        async with db.execute("SELECT id FROM apis WHERE id=?", (api_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, f"API '{api_id}' not found")
        async with db.execute("SELECT COUNT(*) FROM operations WHERE api_id=?", (api_id,)) as cur:
            total = (await cur.fetchone())[0]
        async with db.execute(
            """SELECT id, api_id, operation_id, jentic_id, method, path, summary, description
               FROM operations WHERE api_id=? ORDER BY jentic_id LIMIT ? OFFSET ?""",
            (api_id, limit, offset),
        ) as cur:
            rows = await cur.fetchall()

    total_pages = max(1, (total + limit - 1) // limit)
    has_more = page < total_pages
    base = f"/apis/{api_id}/operations"
    return {
        "data": [_row_to_op(r) for r in rows],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "has_more": has_more,
        "_links": {
            "self": f"{base}?page={page}&limit={limit}",
            **({"next": f"{base}?page={page + 1}&limit={limit}"} if has_more else {}),
            **({"prev": f"{base}?page={page - 1}&limit={limit}"} if page > 1 else {}),
        },
    }


@router.get("/apis/{api_id:path}", summary="Get API summary — name, version, description, and stats", response_model=ApiOut)
async def get_api(api_id: str):
    """Returns API metadata: title, version, description, base URL, vendor, and total operation count. Use GET /apis/{api_id}/operations to enumerate operations."""
    import json as _json, yaml as _yaml
    from pathlib import Path as _Path

    async with get_db() as db:
        async with db.execute(
            "SELECT id, name, description, spec_path, base_url, created_at FROM apis WHERE id=?",
            (api_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, f"API '{api_id}' not found")

    spec_description = row[2]
    spec_path = row[3]

    # Pull description from spec info.description if DB column is empty
    if not spec_description and spec_path:
        try:
            spec_file = _Path(spec_path)
            if spec_file.exists():
                raw = spec_file.read_text()
                doc = _yaml.safe_load(raw) if str(spec_file).endswith((".yaml", ".yml")) else _json.loads(raw)
                spec_description = doc.get("info", {}).get("description")
        except Exception:
            pass

    return {
        "id": row[0],
        "name": row[1],
        "vendor": _extract_vendor(row[0]),
        "description": spec_description,
        "base_url": row[4],
        "created_at": row[5],
    }



@router.delete("/apis", status_code=204, include_in_schema=False)
async def delete_api(
    id: str = Query(..., description="API id to delete, e.g. api.elevenlabs.io"),
    rebuild: bool = Query(False, description="Rebuild BM25 index after delete (slow)")
):
    """Delete an API and all its operations.
    
    By default, does NOT rebuild the search index (performance). Call 
    POST /admin/rebuild-index manually after batch deletes.
    """
    async with get_db() as db:
        async with db.execute("SELECT id FROM apis WHERE id=?", (id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, "API not found")
        await db.execute("DELETE FROM operations WHERE api_id=?", (id,))
        await db.execute("DELETE FROM apis WHERE id=?", (id,))
        await db.commit()
    if rebuild:
        await _rebuild_index()



    """
    Called at startup. Also backfills jentic_id for existing operations
    that were registered before this field was added.
    """
    # Backfill jentic_id for existing operations missing it
    async with get_db() as db:
        # Get all APIs with their spec paths and base URLs
        async with db.execute(
            "SELECT id, spec_path, base_url FROM apis WHERE spec_path IS NOT NULL"
        ) as cur:
            apis = await cur.fetchall()

        for api_id, spec_path, stored_base_url in apis:
            # Resolve base URL: use stored or re-extract from spec
            base_url = stored_base_url or _load_base_url_from_spec(spec_path)

            # Update stored base_url if we just resolved it
            if base_url and not stored_base_url:
                await db.execute(
                    "UPDATE apis SET base_url=? WHERE id=?", (base_url, api_id)
                )

            # Get operations missing jentic_id for this API
            async with db.execute(
                "SELECT id, method, path FROM operations WHERE api_id=? AND (jentic_id IS NULL OR jentic_id='')",
                (api_id,)
            ) as cur:
                stale_ops = await cur.fetchall()

            for op_id, method, path in stale_ops:
                jentic_id = _compute_jentic_id(method or "GET", base_url, path or "/")
                await db.execute(
                    "UPDATE operations SET jentic_id=? WHERE id=?", (jentic_id, op_id)
                )

        await db.commit()

    await _rebuild_index()


@router.post("/admin/rebuild-index", status_code=200, include_in_schema=False)
async def rebuild_search_index():
    """Manually rebuild the BM25 search index from all operations in the DB.
    
    Call this after batch API/operation changes to refresh search results.
    """
    await _rebuild_index()
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM operations") as cur:
            count = (await cur.fetchone())[0]
    return {"status": "ok", "operations_indexed": count}


@router.post("/admin/purge-old-api-ids", status_code=200, include_in_schema=False)
async def purge_old_api_ids():
    """Delete legacy slug-based API IDs, keeping only valid URL-derived IDs.

    Keeps IDs that:
    - contain at least one dot (URL-derived hostname)
    - do NOT start with '{'  (template variable placeholders)
    - are NOT a bare TLD ('com', 'net', 'org', 'io')
    """
    BAD_IDS = {"com", "net", "org", "io", "us", "ai"}

    async with get_db() as db:
        async with db.execute("SELECT id FROM apis") as cur:
            all_ids = [r[0] for r in await cur.fetchall()]

        to_delete = [
            aid for aid in all_ids
            if "." not in aid or aid.startswith("{") or aid in BAD_IDS
        ]

        for aid in to_delete:
            await db.execute("DELETE FROM operations WHERE api_id=?", (aid,))
            await db.execute("DELETE FROM apis WHERE id=?", (aid,))
        await db.commit()

    await _rebuild_index()

    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM apis") as cur:
            api_count = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM operations") as cur:
            op_count = (await cur.fetchone())[0]

    return {
        "status": "ok",
        "deleted": len(to_delete),
        "deleted_ids": to_delete,
        "apis_remaining": api_count,
        "operations_indexed": op_count,
    }


@router.post("/admin/migrate-version-ids", status_code=200, include_in_schema=False)
async def migrate_version_ids():
    """Re-derive all API IDs stripping trailing version segments.

    e.g.  api.openai.com/v1 -> api.openai.com
          api.zoom.us/v2    -> api.zoom.us
          discord.com/api/v10 -> discord.com/api

    On collision (old api.twitter.com/1.1 -> api.twitter.com already exists),
    the conflicting API is deleted rather than renamed.
    """
    renames = []
    deletes = []

    async with get_db() as db:
        async with db.execute("SELECT id, name, base_url FROM apis WHERE base_url IS NOT NULL") as cur:
            rows = await cur.fetchall()
        existing_ids = {r[0] for r in rows}

        for old_id, name, base_url in rows:
            new_id = _derive_api_id(base_url)
            if new_id == old_id:
                continue
            if new_id in existing_ids:
                # Collision — drop the old/versioned duplicate
                deletes.append(old_id)
            else:
                renames.append((old_id, new_id))

        for old_id in deletes:
            await db.execute("DELETE FROM operations WHERE api_id=?", (old_id,))
            await db.execute("DELETE FROM apis WHERE id=?", (old_id,))

        for old_id, new_id in renames:
            await db.execute("UPDATE operations SET api_id=? WHERE api_id=?", (new_id, old_id))
            await db.execute("UPDATE apis SET id=? WHERE id=?", (new_id, old_id))

        await db.commit()

    await _rebuild_index()

    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM apis") as cur:
            api_count = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM operations") as cur:
            op_count = (await cur.fetchone())[0]

    return {
        "status": "ok",
        "renamed": [{"from": o, "to": n} for o, n in renames],
        "deleted_collisions": deletes,
        "apis_remaining": api_count,
        "operations_indexed": op_count,
    }


@router.post("/admin/migrate-capability-ids", status_code=200, include_in_schema=False)
async def migrate_capability_ids():
    """Migrate operation jentic_ids to the current single-slash format: METHOD/host/path.

    Handles two legacy formats:
      - Old: "METHOD https://host/path"   (original format)
      - Mid: "METHOD//host/path"          (double-slash, now superseded)

    Safe to re-run — skips IDs already in the correct single-slash format.
    Rebuilds BM25 index after migration.
    """
    import re as _re
    old_https_re = _re.compile(
        r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+https?://(.+)$", _re.I
    )
    old_dslash_re = _re.compile(
        r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)//(.+)$", _re.I
    )
    migrated = 0
    skipped = 0

    async with get_db() as db:
        async with db.execute("SELECT id, jentic_id FROM operations") as cur:
            rows = await cur.fetchall()

        for (row_id, jentic_id) in rows:
            m = old_https_re.match(jentic_id) or old_dslash_re.match(jentic_id)
            if not m:
                skipped += 1
                continue
            new_id = f"{m.group(1).upper()}/{m.group(2)}"
            await db.execute(
                "UPDATE operations SET jentic_id=? WHERE id=?", (new_id, row_id)
            )
            migrated += 1

        await db.commit()

    await _rebuild_index()
    return {"status": "ok", "migrated": migrated, "skipped_already_new": skipped}


# Alias used by main.py lifespan startup
rebuild_index_on_startup = _rebuild_index
