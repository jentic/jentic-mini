"""
Catalog router — internal manifest for lazy API import.

The catalog manifest is an implementation detail: it maps public API IDs to their
spec locations in jentic/jentic-public-apis. Agents don't need to interact with it
directly — just `POST /credentials` with an api_id and the spec is fetched automatically.

Routes:
  POST /catalog/refresh  — admin: pull fresh manifest from GitHub (auto-refreshes daily)
"""

import json
import logging
import re
import time
import urllib.request
import urllib.error
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from src.db import get_db
from src.config import DATA_DIR
from src.openapi_helpers import agent_hints

log = logging.getLogger("jentic.catalog")

router = APIRouter()

CATALOG_MANIFEST_PATH = DATA_DIR / "catalog_manifest.json"
WORKFLOW_MANIFEST_PATH = DATA_DIR / "workflow_manifest.json"
GITHUB_REPO = "jentic/jentic-public-apis"
GITHUB_API_BASE = "https://api.github.com"
CATALOG_PATH = "apis/openapi"
WORKFLOWS_CATALOG_PATH = "workflows"
MANIFEST_MAX_AGE_SECONDS = 24 * 3600  # auto-refresh if older than 1 day


# ── API Manifest helpers ──────────────────────────────────────────────────────

def _load_manifest() -> list[dict]:
    if not CATALOG_MANIFEST_PATH.exists():
        return []
    try:
        return json.loads(CATALOG_MANIFEST_PATH.read_text())
    except Exception:
        return []


def _save_manifest(entries: list[dict]) -> None:
    CATALOG_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_MANIFEST_PATH.write_text(json.dumps(entries, indent=2))


def _manifest_age_seconds() -> float | None:
    if not CATALOG_MANIFEST_PATH.exists():
        return None
    return time.time() - CATALOG_MANIFEST_PATH.stat().st_mtime


# ── Workflow manifest helpers ─────────────────────────────────────────────────

def _load_workflow_manifest() -> list[dict]:
    if not WORKFLOW_MANIFEST_PATH.exists():
        return []
    try:
        return json.loads(WORKFLOW_MANIFEST_PATH.read_text())
    except Exception:
        return []


def _save_workflow_manifest(entries: list[dict]) -> None:
    WORKFLOW_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WORKFLOW_MANIFEST_PATH.write_text(json.dumps(entries, indent=2))




def _fetch_github_dir(path: str) -> list[dict]:
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/{path}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Jentic-Mini/0.2",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _find_spec_recursive(path: str, depth: int = 0, max_depth: int = 3) -> dict | None:
    """Recursively search a GitHub directory for an OpenAPI spec file.

    Returns the first spec file found (prioritising standard names),
    or None if nothing found within max_depth levels.
    """
    if depth > max_depth:
        return None
    try:
        items = _fetch_github_dir(path)
    except Exception:
        return None

    files = [i for i in items if i["type"] == "file"]
    subdirs = sorted([i for i in items if i["type"] == "dir"], key=lambda x: x["name"], reverse=True)

    # Prefer canonical spec filenames
    for fname in ("openapi.json", "openapi.yaml", "openapi.yml", "swagger.json", "swagger.yaml", "swagger.yml"):
        hit = next((f for f in files if f["name"].lower() == fname), None)
        if hit:
            return hit

    # Recurse into subdirs (sorted latest-first)
    for subdir in subdirs:
        hit = _find_spec_recursive(subdir["path"], depth + 1, max_depth)
        if hit:
            return hit

    return None


async def _get_registered_api_ids() -> set[str]:
    async with get_db() as db:
        async with db.execute("SELECT id FROM apis") as cur:
            rows = await cur.fetchall()
    return {row[0] for row in rows}


def _catalog_vendor_set(api_ids: set[str]) -> set[str]:
    """Return registrable-domain vendors for a set of API ids.

    Used to deduplicate catalog entries against locally registered APIs.
    e.g.  api.stripe.com → stripe.com,  slack.com/api → slack.com
    """
    from src.routers.apis import _extract_vendor
    vendors: set[str] = set()
    for aid in api_ids:
        v = _extract_vendor(aid)
        if v:
            vendors.add(v)
    return vendors


async def ensure_catalog_api_imported(api_id: str) -> str | None:
    """Import (or re-import) a catalog API into the local registry.

    Called by POST/PATCH /credentials so that saving a credential always ensures
    the API has a fresh, complete local registration including its spec file.
    Re-imports even if the API row already exists — this self-heals missing or
    stale spec files without needing a separate repair endpoint.

    Returns the locally-registered api_id after import, or None if the api_id
    isn't in the catalog manifest (caller should proceed without import).

    Raises HTTPException on import failure.
    """
    # In the catalog?
    entries = _load_manifest()
    entry = next((e for e in entries if e["api_id"] == api_id), None)
    if not entry:
        return None  # not a catalog API — caller proceeds as-is

    log.info("Lazy-importing catalog API '%s' for credential add", api_id)
    try:
        spec_file = _find_spec_recursive(entry["path"])
    except Exception as e:
        raise HTTPException(502, f"Error fetching catalog spec for '{api_id}': {e}")

    if not spec_file:
        raise HTTPException(
            404,
            f"No OpenAPI spec file found for catalog API '{api_id}'. "
            f"Cannot auto-import — check the catalog entry at GET /catalog/{api_id}.",
        )

    download_url = spec_file.get("download_url")
    if not download_url:
        raise HTTPException(502, f"No download_url for spec file '{spec_file['name']}'")

    from src.routers.import_ import ImportRequest, ImportSource, import_sources
    safe_name = api_id.replace("/", "_")
    try:
        result = await import_sources(
            ImportRequest(sources=[ImportSource(type="url", url=download_url, filename=f"{safe_name}_{spec_file['name']}", force_api_id=api_id)])
        )
    except Exception as e:
        raise HTTPException(500, f"Auto-import failed for catalog API '{api_id}': {e}")

    imported_id = None
    results = result.get("results", []) if isinstance(result, dict) else []
    if results:
        imported_id = results[0].get("id")
        if results[0].get("status") == "failed":
            log.warning("Lazy-import failed for '%s': %s", api_id, results[0].get("error"))
            raise HTTPException(502, f"Import failed for '{api_id}': {results[0].get('error')}")
    log.info("Lazy-import done for '%s' → registered as '%s'", api_id, imported_id)
    return imported_id or api_id


async def lazy_import_catalog_workflows(api_id: str) -> list[str]:
    """Lazy-import all catalog workflows for the given api_id.

    Called after ensure_catalog_api_imported() so the local spec already exists.
    Fetches the arazzo file from GitHub, rewrites relative sourceDescription URLs
    to point to the locally registered spec, saves one arazzo file per workflow,
    and registers all workflows in the DB.

    Returns list of imported workflow slugs (empty if no workflows found).
    """
    from src.routers.import_ import WORKFLOWS_DIR, _register_arazzo

    # Find in workflow manifest — exact source_id match first, then vendor fallback
    wf_manifest = _load_workflow_manifest()
    source_id = api_id.replace("/", "~", 1)
    entry = next((e for e in wf_manifest if e["source_id"] == source_id), None)

    if not entry:
        # Vendor fallback: api.stripe.com → look for stripe.com in workflow manifest
        from src.routers.apis import _extract_vendor
        vendor = _extract_vendor(api_id)
        if vendor:
            entry = next(
                (e for e in wf_manifest
                 if e["api_id"] == vendor or e["api_id"].startswith(vendor + "/")),
                None,
            )
            if entry:
                source_id = entry["source_id"]
                log.debug("Workflow vendor fallback: '%s' → source_id '%s'", api_id, source_id)

    if not entry:
        log.debug("No catalog workflows found for '%s' (source_id='%s')", api_id, source_id)
        return []

    # Fetch arazzo from GitHub raw
    raw_url = (
        f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/"
        f"{entry['path']}/workflows.arazzo.json"
    )
    try:
        req = urllib.request.Request(raw_url, headers={"User-Agent": "Jentic-Mini/0.2"})
        with urllib.request.urlopen(req, timeout=30) as r:
            doc = json.loads(r.read())
    except Exception as e:
        log.warning("Could not fetch catalog workflows for '%s': %s", api_id, e)
        return []

    # Rewrite relative sourceDescription URLs → local spec path
    async with get_db() as db:
        async with db.execute("SELECT spec_path FROM apis WHERE id=?", (api_id,)) as cur:
            row = await cur.fetchone()
    local_spec_path = row[0] if row else None

    if local_spec_path:
        for src in doc.get("sourceDescriptions", []):
            if src.get("url", "").startswith("./"):
                src["url"] = local_spec_path
    else:
        log.warning(
            "No local spec found for '%s'; workflows may fail at execution (sourceDescriptions not rewritten)",
            api_id,
        )

    # Import each workflow as a separate single-workflow arazzo file
    safe_id = re.sub(r"[^a-z0-9_-]", "_", source_id.lower())
    imported_slugs: list[str] = []
    workflows_root = WORKFLOWS_DIR.resolve()

    for wf in doc.get("workflows", []):
        workflow_id = wf.get("workflowId", "")
        if not workflow_id:
            continue

        slug = re.sub(r"[^a-z0-9-]", "-", workflow_id.lower()).strip("-")[:60]
        slug = re.sub(r"-+", "-", slug)

        # Save as a single-workflow arazzo file so execution always picks the right one
        single_doc = {**doc, "workflows": [wf]}
        arazzo_file = (WORKFLOWS_DIR / f"catalog_{safe_id}_{slug}.json").resolve()
        try:
            arazzo_file.relative_to(workflows_root)
        except ValueError:
            log.warning("Path traversal blocked for workflow '%s'", workflow_id)
            continue
        arazzo_path = str(arazzo_file)
        with open(arazzo_path, "w") as f:
            json.dump(single_doc, f, indent=2)

        try:
            result = await _register_arazzo(single_doc, arazzo_path, slug_hint=slug)
            imported_slugs.append(result["slug"])
        except Exception as e:
            log.warning("Failed to import workflow '%s' for '%s': %s", workflow_id, api_id, e)

    log.info(
        "Imported %d workflow(s) for '%s': %s",
        len(imported_slugs), api_id,
        imported_slugs[:5] if len(imported_slugs) > 5 else imported_slugs,
    )
    return imported_slugs


# ── Catalog manifest builder (apis.json + GitHub Contents API) ────────────────

_APIS_JSON_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{CATALOG_PATH}/apis.json"
_VERSION_SUBDIR_RE = re.compile(r"^(main|master|latest|heads|v\d|[0-9])", re.IGNORECASE)


def _build_manifest_from_apis_json() -> list[dict] | None:
    """Build the catalog manifest from the curated apis.json index file.

    Returns a list of manifest entries, or None if the fetch fails.
    This is the preferred method — a single HTTP fetch with no truncation
    and full umbrella vendor expansion.
    """
    try:
        req = urllib.request.Request(
            _APIS_JSON_URL,
            headers={"User-Agent": "Jentic-Mini/0.2"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        log.warning("Failed to fetch apis.json: %s", exc)
        return None

    includes = data.get("include", [])
    if not includes:
        log.warning("apis.json has no include entries")
        return None

    manifest: list[dict] = []
    seen: set[str] = set()
    for entry in includes:
        url = entry.get("url", "")
        # Extract api_id from URL: .../apis/openapi/{domain}/{sub}/{version}/apis.json
        m = re.search(r"/apis/openapi/([^/]+)/([^/]+)/([^/]+)/apis\.json", url)
        if not m:
            continue
        domain, sub, _version = m.groups()
        if _VERSION_SUBDIR_RE.match(sub):
            api_id = domain
        else:
            api_id = f"{domain}/{sub}"
        # Deduplicate (multiple versions of the same API)
        if api_id in seen:
            continue
        seen.add(api_id)
        path = f"{CATALOG_PATH}/{domain}/{sub}" if sub != domain else f"{CATALOG_PATH}/{domain}"
        # Derive spec_url from the sub-apis.json URL: replace /apis.json → /openapi.json
        spec_url = url.replace("/apis.json", "/openapi.json") if url.endswith("/apis.json") else None
        manifest.append({"api_id": api_id, "path": path, "sha": "", "spec_url": spec_url})

    return manifest


# ── Startup helper (called from lifespan) ────────────────────────────────────

async def refresh_catalog_if_stale() -> None:
    """Auto-refresh both API and workflow manifests on startup if absent or stale."""
    age = _manifest_age_seconds()
    if age is None or age > MANIFEST_MAX_AGE_SECONDS:
        log.info("Catalog manifest stale or absent — refreshing from GitHub")
        try:
            # API manifest from curated apis.json index (single fetch, no truncation)
            api_entries = _build_manifest_from_apis_json()

            # Workflow manifest from GitHub Contents API (single call)
            try:
                wf_items = _fetch_github_dir(WORKFLOWS_CATALOG_PATH)
                wf_entries = sorted([
                    {
                        "source_id": i["name"],
                        "path": i["path"],
                        "api_id": i["name"].replace("~", "/", 1),
                    }
                    for i in wf_items
                    if i.get("type") == "dir"
                ], key=lambda e: e["source_id"])
            except Exception as wf_exc:
                log.warning("Workflow manifest fetch failed — keeping previous: %s", wf_exc)
                wf_entries = None
            if api_entries is None:
                log.warning("apis.json fetch failed — keeping previous API manifest")
            else:
                _save_manifest(sorted(api_entries, key=lambda e: e["api_id"]))
            if wf_entries is not None:
                _save_workflow_manifest(wf_entries)
            log.info(
                "Manifests refreshed: %s API entries, %d workflow sources",
                len(api_entries) if api_entries else "unchanged", len(wf_entries),
            )
        except Exception as e:
            log.warning("Catalog manifest refresh failed (non-fatal): %s", e)
    else:
        log.info(
            "Catalog manifest up to date (age %.0fs, %d API entries, %d workflow sources)",
            age, len(_load_manifest()), len(_load_workflow_manifest()),
        )


# ── Search helpers ────────────────────────────────────────────────────────────

def _tokenise(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _score_entry(api_id: str, q_tokens: list[str]) -> float:
    """Simple token overlap score — no need for full BM25 over domain names."""
    name_tokens = _tokenise(api_id)
    if not name_tokens:
        return 0.0
    matches = sum(1.0 for t in q_tokens if any(t in nt for nt in name_tokens))
    return matches / max(len(q_tokens), 1)


def _search_manifest(entries: list[dict], q: str | None, limit: int) -> list[dict]:
    if not q or not q.strip():
        return entries[:limit]
    q_tokens = _tokenise(q)
    if not q_tokens:
        return entries[:limit]
    scored = [(e, _score_entry(e["api_id"], q_tokens)) for e in entries]
    scored = [(e, s) for e, s in scored if s > 0]
    scored.sort(key=lambda x: -x[1])
    return [e for e, _ in scored[:limit]]


def _build_catalog_result(entry: dict, registered_ids: set[str]) -> dict:
    api_id = entry["api_id"]
    is_reg = api_id in registered_ids
    links: dict = {"github": f"https://github.com/{GITHUB_REPO}/tree/main/{entry['path']}"}
    if is_reg:
        links["api"] = f"/apis/{api_id}"
        links["operations"] = f"/apis/{api_id}/operations"
    else:
        links["import"] = f"/catalog/{api_id}/import"
    result = {
        "type": "catalog_api",
        "source": "catalog",
        "api_id": api_id,
        "registered": is_reg,
        "_links": links,
    }
    if entry.get("spec_url"):
        result["spec_url"] = entry["spec_url"]
    return result


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "/catalog",
    summary="List the public API catalog",
    tags=["catalog"],
    openapi_extra=agent_hints(
        when_to_use="Use to browse available APIs from the Jentic public catalog (jentic/jentic-public-apis GitHub repo). Returns list of catalog entries with api_id and registration status. Use ?q= to filter by API ID substring, ?registered_only=true to see only locally registered APIs, ?unregistered_only=true to see only APIs not yet imported. Catalog manifest auto-refreshes daily; use POST /catalog/refresh to sync immediately.",
        prerequisites=["Requires authentication (toolkit key or human session)"],
        avoid_when="Do not use to list locally registered APIs — use GET /apis?source=local instead. Do not use for natural language API discovery — use GET /search for that.",
        related_operations=[
            "GET /catalog/{api_id} — get spec download URL for a catalog API",
            "POST /import — import a catalog API after finding it here",
            "POST /catalog/refresh — refresh catalog manifest from GitHub if empty or stale",
            "GET /apis — list locally registered APIs (includes both local and catalog sources)"
        ]
    ),
)
async def list_catalog(
    q: Annotated[str | None, Query(description="Search term to filter APIs by name or description")] = None,
    limit: Annotated[int, Query(description="Maximum number of results (1-500)", ge=1, le=500)] = 50,
    registered_only: Annotated[bool, Query(description="Return only APIs already registered locally")] = False,
    unregistered_only: Annotated[bool, Query(description="Return only APIs not yet registered locally")] = False,
):
    """Returns entries from the cached public API catalog manifest.
    Use ``POST /catalog/refresh`` to sync from GitHub first if the list is empty.
    """
    entries = _load_manifest()
    registered_ids = await _get_registered_api_ids()

    if registered_only:
        entries = [e for e in entries if e["api_id"] in registered_ids]
    elif unregistered_only:
        entries = [e for e in entries if e["api_id"] not in registered_ids]

    if q:
        entries = _search_manifest(entries, q, limit)
    else:
        entries = entries[:limit]

    results = [_build_catalog_result(e, registered_ids) for e in entries]
    manifest = _load_manifest()
    age = _manifest_age_seconds()
    return {
        "data": results,
        "total": len(results),
        "catalog_total": len(manifest),
        "manifest_age_seconds": age,
        "status": "ok" if manifest else "empty",
    }


@router.get(
    "/catalog/{api_id:path}",
    summary="Get a catalog entry with spec location",
    tags=["catalog"],
    openapi_extra=agent_hints(
        when_to_use="Use after finding an API via GET /catalog to retrieve the spec download URL for import. Returns api_id, registration status, spec_url (GitHub raw file URL), and spec_filename. Use the spec_url with POST /import to register this API locally. Recursively searches the GitHub directory for OpenAPI spec files (openapi.json, openapi.yaml, etc.).",
        prerequisites=[
            "Requires authentication (toolkit key or human session)",
            "Valid catalog api_id from GET /catalog (format: hostname or hostname/path)"
        ],
        avoid_when="Do not use for APIs already registered locally — check GET /apis first. Do not use to download the spec directly (use POST /import instead).",
        related_operations=[
            "GET /catalog — browse catalog to find the api_id",
            "POST /import — import the API using the spec_url returned here",
            "GET /apis — check if API is already registered before importing",
            "POST /credentials — add credentials after importing"
        ]
    ),
)
async def get_catalog_entry(api_id: Annotated[str, Path(description="API ID from catalog to retrieve")]):
    """Return details for a single catalog API, including the spec download URL.

    Use the returned `spec_url` with `POST /import` to import this API:

        POST /import
        {"sources": [{"type": "url", "url": "<spec_url>", "force_api_id": "<api_id>"}]}
    """
    entries = _load_manifest()
    entry = next((e for e in entries if e["api_id"] == api_id), None)
    if not entry:
        raise HTTPException(404, f"'{api_id}' not found in the public catalog.")

    async with get_db() as db:
        async with db.execute("SELECT 1 FROM apis WHERE id=? LIMIT 1", (api_id,)) as cur:
            is_registered = await cur.fetchone() is not None

    # Use cached spec_url from manifest if available (avoids GitHub API walk)
    spec_url: str | None = entry.get("spec_url")
    spec_file = None
    spec_error = None
    if not spec_url:
        # Fallback: walk GitHub tree (for manifests built before spec_url was added)
        try:
            spec_file = _find_spec_recursive(entry["path"])
            if spec_file:
                spec_url = spec_file.get("download_url")
        except urllib.error.HTTPError as e:
            spec_error = f"GitHub returned {e.code}: {e.reason}"
        except Exception as e:
            spec_error = str(e)

    links: dict = {
        "github": f"https://github.com/{GITHUB_REPO}/tree/main/{entry['path']}",
    }
    if is_registered:
        links["api"] = f"/apis/{api_id}"
        links["operations"] = f"/apis/{api_id}/operations"
    if spec_url:
        links["import"] = "/import"

    result: dict = {
        "api_id": api_id,
        "registered": is_registered,
        "spec_url": spec_url,
        "spec_filename": spec_file["name"] if spec_file else None,
        "_links": links,
    }
    if spec_error:
        result["spec_error"] = spec_error
    return result


@router.post(
    "/catalog/refresh",
    summary="Refresh the API catalog manifest from GitHub",
    tags=["admin"],
    openapi_extra=agent_hints(
        when_to_use="Use when the catalog is empty (GET /catalog returns empty list) or when you need immediate sync after a new API was added to jentic/jentic-public-apis on GitHub. Fetches the curated apis.json index and workflows directory listing from GitHub (two unauthenticated HTTP requests). Manifest auto-refreshes daily on startup, so only call explicitly if you need immediate sync.",
        prerequisites=["Requires authentication (admin/human session)"],
        avoid_when="Do not call repeatedly — safe but unnecessary since manifest auto-refreshes daily. Do not use to import APIs — use POST /import after refreshing.",
        related_operations=[
            "GET /catalog — list catalog entries after refreshing",
            "GET /catalog/{api_id} — get spec URL for an API after refreshing",
            "POST /import — import an API after finding it in the refreshed catalog"
        ]
    ),
)
async def refresh_catalog():
    """Rebuilds the internal catalog manifest from the jentic/jentic-public-apis repository.
    The manifest is used by lazy import — when you `POST /credentials` for an API not yet in
    your local registry, Jentic Mini resolves the spec from this manifest automatically.

    Fetches the curated apis.json index and the workflows directory listing
    (two unauthenticated HTTP requests). Safe to call repeatedly.
    The manifest auto-refreshes daily; only call this explicitly if you need immediate sync
    after a new API has been added to the public catalog.
    """
    try:
        api_entries = _build_manifest_from_apis_json()
        if api_entries is None:
            raise HTTPException(502, "Failed to fetch apis.json from GitHub")
        wf_items = _fetch_github_dir(WORKFLOWS_CATALOG_PATH)
        wf_entries = sorted([
            {
                "source_id": i["name"],
                "path": i["path"],
                "api_id": i["name"].replace("~", "/", 1),
            }
            for i in wf_items
            if i.get("type") == "dir"
        ], key=lambda e: e["source_id"])
    except urllib.error.HTTPError as e:
        raise HTTPException(502, f"GitHub returned {e.code}: {e.reason}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch catalog from GitHub: {e}")

    _save_manifest(sorted(api_entries, key=lambda e: e["api_id"]))
    _save_workflow_manifest(wf_entries)
    log.info(
        "Manifests refreshed: %d API entries, %d workflow sources",
        len(api_entries), len(wf_entries),
    )
    return {
        "status": "ok",
        "api_entries": len(api_entries),
        "workflow_sources": len(wf_entries),
        "fetched_at": time.time(),
    }
