"""
Catalog router — browse the jentic-public-apis public catalog.

Endpoints:
  GET  /catalog                    — list / search catalog (BM25 over manifest)
  POST /catalog/refresh            — admin: pull fresh manifest from GitHub
  GET  /catalog/{api_id}           — inspect a single catalog entry

Design:
  - The manifest is a lightweight JSON file (~1-2 MB) cached at CATALOG_MANIFEST_PATH.
  - Specs are NOT cloned in bulk — they are fetched on demand (lazy import) when
    an agent adds a credential for a catalog API via POST /credentials.
  - The GitHub repo (jentic/jentic-public-apis) is public — no auth required.
"""

import json
import logging
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.db import get_db

log = logging.getLogger("jentic.catalog")

router = APIRouter()

CATALOG_MANIFEST_PATH = Path("/app/data/catalog_manifest.json")
WORKFLOW_MANIFEST_PATH = Path("/app/data/workflow_manifest.json")
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


def _build_workflow_manifest_from_tree(tree_entries: list[dict]) -> list[dict]:
    """Build the workflow manifest from a full recursive git tree.

    Workflow dirs are at workflows/<source_id>/ where source_id uses:
      - plain domain: workflows/stripe.com/
      - sub-api with ~: workflows/atlassian.com~jira/
      - multi-api with +: workflows/vendorA.com+vendorB.com/ (rare)

    Each entry maps source_id → api_id (replacing first ~ with /).
    """
    prefix = "workflows/"
    manifest: list[dict] = []
    seen: set[str] = set()
    for entry in tree_entries:
        if entry.get("type") != "tree":
            continue
        path = entry["path"]
        if not path.startswith(prefix):
            continue
        rel = path[len(prefix):]
        # Only top-level dirs (no nested slash)
        if "/" in rel:
            continue
        source_id = rel
        if source_id in seen:
            continue
        seen.add(source_id)
        # Convert source_id → api_id: first ~ becomes /
        api_id = source_id.replace("~", "/", 1)
        manifest.append({
            "source_id": source_id,
            "path": path,
            "api_id": api_id,
        })
    return sorted(manifest, key=lambda e: e["source_id"])


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
    """Lazy-import a catalog API if it isn't already in the local registry.

    Called by POST /credentials when the target api_id isn't locally registered.
    Returns the locally-registered api_id after import, or None if the api_id
    isn't in the catalog manifest (caller should proceed without import).

    Raises HTTPException on import failure.
    """
    # Already registered?
    async with get_db() as db:
        async with db.execute("SELECT id FROM apis WHERE id=?", (api_id,)) as cur:
            if await cur.fetchone():
                return api_id  # already local

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
    try:
        result = await import_sources(
            ImportRequest(sources=[ImportSource(type="url", url=download_url, filename=f"{api_id}_{spec_file['name']}")])
        )
    except Exception as e:
        raise HTTPException(500, f"Auto-import failed for catalog API '{api_id}': {e}")

    imported_id = None
    results = result.get("results", []) if isinstance(result, dict) else []
    if results:
        imported_id = results[0].get("id")
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

    for wf in doc.get("workflows", []):
        workflow_id = wf.get("workflowId", "")
        if not workflow_id:
            continue

        slug = re.sub(r"[^a-z0-9-]", "-", workflow_id.lower()).strip("-")[:60]
        slug = re.sub(r"-+", "-", slug)

        # Save as a single-workflow arazzo file so execution always picks the right one
        single_doc = {**doc, "workflows": [wf]}
        arazzo_path = str(WORKFLOWS_DIR / f"catalog_{safe_id}_{slug}.json")
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


# ── Tree-based manifest builder ───────────────────────────────────────────────

_VERSION_BRANCH_RE = re.compile(r"^(main|master|latest|heads|v\d|[0-9])", re.IGNORECASE)


def _fetch_full_tree() -> list[dict] | None:
    """Fetch the full recursive git tree for the repo in a single API call.

    Returns the list of tree entries, or None if the response was truncated
    (fallback to shallow approach in that case).
    """
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/git/trees/main?recursive=1"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Jentic-Mini/0.2",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read())
    if data.get("truncated"):
        log.warning("GitHub tree API response truncated — falling back to shallow manifest")
        return None
    return data.get("tree", [])


def _build_manifest_from_tree(tree_entries: list[dict]) -> list[dict]:
    """Build a detailed catalog manifest from a full recursive git tree.

    Detects umbrella vendors (e.g. googleapis.com, atlassian.com) whose
    immediate subdirectories are product/API names rather than version branches,
    and expands them to individual sub-API entries.

    Heuristic: a top-level directory is a leaf API if ANY of its first-level
    children matches a version/branch pattern (main, master, v1, 1.0, etc.).
    Otherwise it's an umbrella vendor — expand each child as a separate api_id.
    """
    prefix = "apis/openapi/"

    # Build a mapping: top-level domain → set of immediate child dir names
    top_level: dict[str, set[str]] = {}
    top_level_sha: dict[str, str] = {}

    for entry in tree_entries:
        if entry.get("type") != "tree":
            continue
        path = entry["path"]
        if not path.startswith(prefix):
            continue
        rel = path[len(prefix):]
        parts = rel.split("/")
        if len(parts) == 1:
            domain = parts[0]
            if domain not in top_level:
                top_level[domain] = set()
                top_level_sha[domain] = entry.get("sha", "")
        elif len(parts) == 2:
            domain, child = parts
            if domain in top_level:
                top_level[domain].add(child)

    manifest: list[dict] = []
    for domain in sorted(top_level.keys()):
        children = top_level[domain]
        if not children:
            # Empty dir — skip
            continue
        if any(_VERSION_BRANCH_RE.match(c) for c in children):
            # Leaf API: the domain IS the api_id
            manifest.append({
                "api_id": domain,
                "path": f"{prefix}{domain}",
                "sha": top_level_sha.get(domain, ""),
            })
        else:
            # Umbrella vendor: expand to sub-APIs
            for sub in sorted(children):
                manifest.append({
                    "api_id": f"{domain}/{sub}",
                    "path": f"{prefix}{domain}/{sub}",
                    "sha": "",  # sha for sub-dir not easily available here
                })

    return manifest


def _build_manifest_shallow() -> list[dict]:
    """Fallback: build manifest from top-level directory listing only (no umbrella expansion)."""
    items = _fetch_github_dir(CATALOG_PATH)
    return [
        {"api_id": i["name"], "path": i["path"], "sha": i.get("sha", "")}
        for i in items
        if i.get("type") == "dir"
    ]


# ── Startup helper (called from lifespan) ────────────────────────────────────

async def refresh_catalog_if_stale() -> None:
    """Auto-refresh both API and workflow manifests on startup if absent or stale."""
    age = _manifest_age_seconds()
    if age is None or age > MANIFEST_MAX_AGE_SECONDS:
        log.info("Catalog manifest stale or absent — fetching from GitHub (tree API)")
        try:
            tree = _fetch_full_tree()
            if tree is not None:
                api_entries = _build_manifest_from_tree(tree)
                wf_entries = _build_workflow_manifest_from_tree(tree)
                method = "tree"
            else:
                api_entries = _build_manifest_shallow()
                wf_entries = []
                method = "shallow_fallback"
            _save_manifest(api_entries)
            _save_workflow_manifest(wf_entries)
            log.info(
                "Manifests refreshed via %s: %d API entries, %d workflow sources",
                method, len(api_entries), len(wf_entries),
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
    return {
        "type": "catalog_api",
        "source": "catalog",
        "api_id": api_id,
        "registered": is_reg,
        "_links": links,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "/catalog",
    summary="Browse the Jentic public API catalog",
    tags=["catalog"],
)
async def list_catalog(
    q: str | None = Query(None, description='Filter by API name/domain, e.g. "stripe" or "slack"'),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
    registered_only: bool = Query(False, description="Only show APIs already imported into your registry"),
    unregistered_only: bool = Query(False, description="Only show APIs not yet in your registry"),
):
    """Browse and search the public Jentic API catalog (jentic/jentic-public-apis).

    Returns individual APIs including expanded sub-APIs for umbrella vendors
    (e.g. googleapis.com/gmail, googleapis.com/calendar, atlassian.com/jira).
    Results show `registered: true/false` to distinguish APIs already in your local
    registry from those available to use.

    To use a catalog API: call `POST /credentials` with its `api_id` — the spec
    is imported automatically. Manifest is auto-refreshed daily; force a refresh
    via `POST /catalog/refresh`.
    """
    entries = _load_manifest()
    if not entries:
        return {
            "status": "empty",
            "message": "Catalog manifest not loaded. Call POST /catalog/refresh to sync.",
            "refresh_url": "/catalog/refresh",
            "total": 0,
            "data": [],
        }

    registered_ids = await _get_registered_api_ids()
    matched = _search_manifest(entries, q, limit * 3)  # over-fetch to allow filter

    out = []
    for e in matched:
        is_reg = e["api_id"] in registered_ids
        if registered_only and not is_reg:
            continue
        if unregistered_only and is_reg:
            continue
        out.append(_build_catalog_result(e, registered_ids))
        if len(out) >= limit:
            break

    age = _manifest_age_seconds()
    return {
        "total": len(out),
        "catalog_total": len(entries),
        "manifest_age_seconds": round(age) if age is not None else None,
        "data": out,
    }


@router.post(
    "/catalog/refresh",
    summary="Refresh the catalog manifest from GitHub",
    tags=["catalog"],
)
async def refresh_catalog():
    """Fetches the full recursive git tree from jentic/jentic-public-apis and builds
    a detailed manifest that correctly identifies individual APIs within umbrella vendors
    (e.g. googleapis.com expands to googleapis.com/gmail, googleapis.com/calendar, etc.).

    Takes ~2-5 seconds (two unauthenticated GitHub API calls). Safe to call repeatedly.
    Falls back to a shallow top-level listing if the tree response is truncated.
    """
    try:
        tree = _fetch_full_tree()
        if tree is not None:
            api_entries = _build_manifest_from_tree(tree)
            wf_entries = _build_workflow_manifest_from_tree(tree)
            method = "tree"
        else:
            api_entries = _build_manifest_shallow()
            wf_entries = []
            method = "shallow_fallback"
    except urllib.error.HTTPError as e:
        raise HTTPException(502, f"GitHub returned {e.code}: {e.reason}")
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch catalog from GitHub: {e}")

    _save_manifest(api_entries)
    _save_workflow_manifest(wf_entries)
    log.info(
        "Manifests refreshed via %s: %d API entries, %d workflow sources",
        method, len(api_entries), len(wf_entries),
    )
    return {
        "status": "ok",
        "api_entries": len(api_entries),
        "workflow_sources": len(wf_entries),
        "method": method,
        "fetched_at": time.time(),
    }


@router.get(
    "/catalog/{api_id:path}",
    summary="Inspect a catalog entry",
    tags=["catalog"],
)
async def get_catalog_entry(api_id: str):
    """Inspect a single catalog API entry. Shows registration status, GitHub link,
    and available spec files (fetched live from GitHub).

    Note: this makes a live GitHub API call to list the directory contents.
    """
    entries = _load_manifest()
    entry = next((e for e in entries if e["api_id"] == api_id), None)
    if not entry:
        raise HTTPException(
            404,
            f"'{api_id}' not found in catalog. Run POST /catalog/refresh to update the manifest.",
        )

    # Fetch directory listing to show available versions/files
    try:
        items = _fetch_github_dir(entry["path"])
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch catalog entry from GitHub: {e}")

    registered_ids = await _get_registered_api_ids()
    is_reg = api_id in registered_ids

    # Summarise available versions / files
    subdirs = [i for i in items if i["type"] == "dir"]
    files = [i for i in items if i["type"] == "file"]
    spec_files = [f for f in files if f["name"].lower().endswith((".json", ".yaml", ".yml"))]

    return {
        "api_id": api_id,
        "registered": is_reg,
        "github_path": entry["path"],
        "github_url": f"https://github.com/{GITHUB_REPO}/tree/main/{entry['path']}",
        "versions": [s["name"] for s in subdirs],
        "spec_files": [{"name": f["name"], "size": f["size"], "download_url": f["download_url"]} for f in spec_files],
        "_links": {
            "credentials": f"/credentials?api_id={api_id}",
            "api": f"/apis/{api_id}" if is_reg else None,
        },
    }
