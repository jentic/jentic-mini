"""BM25 search over registered operations AND workflows, with automatic catalog blending."""

from fastapi import APIRouter, Query

import src.bm25 as bm25
from src.models import SearchResult
from src.openapi_helpers import agent_hints
from src.routers.catalog import (
    GITHUB_REPO,
    _get_registered_api_ids,
    _load_manifest,
    _load_workflow_manifest,
    _search_manifest,
)
from src.utils import abbreviate


router = APIRouter()

_OP_INTERNAL_KEYS = {"_id", "_operation_id", "_api_id", "_vendor"}


def _op_links(op_id: str, api_id: str) -> dict:
    """Build _links for an operation result."""
    links = {"inspect": f"/inspect/{op_id}"}
    if api_id:
        links["api"] = f"/apis/{api_id}"
        links["operations"] = f"/apis/{api_id}/operations"
    return links


def _workflow_links(slug: str, wf_id: str) -> dict:
    """Build _links for a workflow result."""
    return {
        "inspect": f"/inspect/{wf_id}",
        "definition": f"/workflows/{slug}",
    }


@router.get(
    "/search",
    summary="Search the catalog — find operations and workflows by natural language intent",
    response_model=list[SearchResult],
    openapi_extra=agent_hints(
        when_to_use="Use when you need to discover APIs or workflows based on a natural language description of what you want to do. Primary entry point for finding capabilities — search first before exploring individual APIs.",
        prerequisites=["Requires authentication (toolkit key or human session)"],
        avoid_when="Do not use if you already know the exact operation ID or workflow slug — use GET /inspect/{id} directly instead.",
        related_operations=[
            "GET /inspect/{id} — get full operation details after finding it via search",
            "GET /apis — browse APIs by provider when you know the vendor",
            "GET /workflows — list all workflows when browsing by category",
        ],
    ),
)
async def search(
    q: str = Query(..., description='Search query, e.g. "send an email" or "create payment"'),
    n: int = Query(10, ge=1, le=100, description="Number of results to return"),
):
    """BM25 search over all registered API operations, Arazzo workflows, and the Jentic public API catalog.

    Returns id, summary, description (≤3 sentences), type, score, and _links.
    - `source: "local"` — operation or workflow in your local registry
    - `source: "catalog"` — API available from the Jentic public catalog; add credentials to use

    _links.inspect → GET /inspect/{id} for full schema and auth detail.
    _links.execute → broker URL to call directly once ready.
    Typical flow: search → inspect → execute.
    """
    results = bm25.search(q, n)
    out = []
    for doc, score in results:
        doc_type = doc.get("type", "operation")
        if doc_type == "workflow":
            wf_id = doc.get("id", "")
            slug = doc.get("slug", "")
            out.append(
                {
                    "type": "workflow",
                    "source": "local",
                    "id": wf_id,
                    "slug": slug,
                    "summary": doc.get("summary") or doc.get("name"),
                    "description": abbreviate(doc.get("description", "") or ""),
                    "involved_apis": doc.get("involved_apis", []),
                    "score": round(score, 4),
                    "_links": _workflow_links(slug, wf_id),
                }
            )
        else:
            op_id = doc.get("id", "")
            api_id = doc.get("_api_id") or ""
            if not api_id and "/" in op_id:
                parts = op_id.split("/", 2)
                api_id = parts[1] if len(parts) >= 2 else ""
            clean = {k: v for k, v in doc.items() if k not in _OP_INTERNAL_KEYS}
            if "description" in clean:
                clean["description"] = abbreviate(clean["description"] or "")
            out.append(
                {
                    "type": "operation",
                    "source": "local",
                    **clean,
                    "score": round(score, 4),
                    "_links": _op_links(op_id, api_id),
                }
            )

    # ── Catalog blending (always-on) ──────────────────────────────────────────
    manifest = _load_manifest()
    if manifest:
        registered_ids = await _get_registered_api_ids()

        # Precise dedup: sub-apis by subdomain coverage, leaves by vendor
        _GENERIC_SUBS = {"api", "www", "app", "web", "portal", "v1", "v2", "v3"}
        covered_sub_apis: set[str] = set()
        covered_leaf_vendors: set[str] = set()
        for local_id in registered_ids:
            hostname = local_id.split("/")[0]
            parts = hostname.split(".")
            if len(parts) < 2:
                continue
            vendor = ".".join(parts[-2:])
            sub = ".".join(parts[:-2]) if len(parts) > 2 else ""
            if sub and sub not in _GENERIC_SUBS:
                covered_sub_apis.add(f"{vendor}/{sub}")
            covered_leaf_vendors.add(vendor)

        catalog_matches = _search_manifest(manifest, q, n)
        for entry in catalog_matches:
            api_id = entry["api_id"]
            if api_id in registered_ids:
                continue
            if "/" in api_id:
                if api_id in covered_sub_apis:
                    continue
            else:
                vendor = (
                    (api_id.split(".")[-2] + "." + api_id.split(".")[-1])
                    if "." in api_id
                    else api_id
                )
                if vendor in covered_leaf_vendors:
                    continue
            out.append(
                {
                    "type": "catalog_api",
                    "source": "catalog",
                    "id": api_id,
                    "api_id": api_id,
                    "summary": f"{api_id} — available in Jentic public catalog",
                    "description": None,
                    "score": 0.0,
                    "_links": {
                        "catalog": f"/catalog/{api_id}",
                        "credentials": "/credentials",
                        "github": f"https://github.com/{GITHUB_REPO}/tree/main/{entry['path']}",
                    },
                }
            )

    # ── Catalog workflow blending ──────────────────────────────────────────────
    wf_manifest = _load_workflow_manifest()
    if wf_manifest and q:
        # Match workflow sources by source_id/api_id
        wf_matches = [
            e
            for e in wf_manifest
            if q.lower() in e["source_id"].lower() or q.lower() in e["api_id"].lower()
        ][:n]
        for entry in wf_matches:
            api_id = entry["api_id"]
            # Only surface catalog workflow sources not already represented locally
            if api_id in registered_ids:
                continue
            if "/" in api_id:
                if api_id in covered_sub_apis:
                    continue
            else:
                vendor = (
                    (api_id.split(".")[-2] + "." + api_id.split(".")[-1])
                    if "." in api_id
                    else api_id
                )
                if vendor in covered_leaf_vendors:
                    continue
            out.append(
                {
                    "type": "catalog_workflow_source",
                    "source": "catalog",
                    "id": f"catalog:workflows:{entry['source_id']}",
                    "api_id": api_id,
                    "summary": f"{api_id} workflows — available in Jentic public catalog",
                    "description": f"Multi-step Arazzo workflows for {api_id}. Add credentials to import.",
                    "score": 0.0,
                    "_links": {
                        "catalog_api": f"/catalog/{api_id}",
                        "workflows": f"/workflows?source=catalog&q={api_id}",
                        "credentials": "/credentials",
                        "github": f"https://github.com/{GITHUB_REPO}/tree/main/{entry['path']}",
                    },
                }
            )

    return out
