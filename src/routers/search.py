"""BM25 search over registered operations AND workflows."""
from urllib.parse import quote
from fastapi import APIRouter, Query
from src.utils import abbreviate
from src.models import SearchResult
import src.bm25 as bm25

router = APIRouter()

_OP_INTERNAL_KEYS = {"_id", "_operation_id", "_api_id", "_vendor"}


def _op_links(op_id: str, api_id: str) -> dict:
    """Build _links for an operation result."""
    encoded = quote(op_id, safe="")
    links = {"inspect": f"/inspect/{op_id}"}
    if api_id:
        links["api"] = f"/apis/{api_id}"
        links["operations"] = f"/apis/{api_id}/operations"
    return links


def _workflow_links(slug: str, wf_id: str) -> dict:
    """Build _links for a workflow result."""
    encoded = quote(wf_id, safe="")
    return {
        "inspect": f"/inspect/{wf_id}",
        "definition": f"/workflows/{slug}",
    }


@router.get(
    "/search",
    summary="Search the catalog — find operations and workflows by natural language intent",
    response_model=list[SearchResult],
)
async def search(
    q: str = Query(..., description='Search query, e.g. "send an email" or "create payment"'),
    n: int = Query(10, ge=1, le=100, description="Number of results to return"),
):
    """BM25 search over all registered API operations and Arazzo workflows.
    Returns id, summary, description (≤3 sentences), type (operation|workflow), score, and _links.
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
            out.append({
                "type": "workflow",
                "id": wf_id,
                "slug": slug,
                "summary": doc.get("summary") or doc.get("name"),
                "description": abbreviate(doc.get("description", "") or ""),
                "involved_apis": doc.get("involved_apis", []),
                "score": round(score, 4),
                "_links": _workflow_links(slug, wf_id),
            })
        else:
            op_id = doc.get("id", "")
            # _api_id is the full api_id (e.g. "api.elevenlabs.io"); fall back to parsing the capability ID
            api_id = doc.get("_api_id") or ""
            if not api_id and "/" in op_id:
                parts = op_id.split("/", 2)   # ["METHOD", "host", "path"]
                api_id = parts[1] if len(parts) >= 2 else ""
            clean = {k: v for k, v in doc.items() if k not in _OP_INTERNAL_KEYS}
            if "description" in clean:
                clean["description"] = abbreviate(clean["description"] or "")
            out.append({
                "type": "operation",
                **clean,
                "score": round(score, 4),
                "_links": _op_links(op_id, api_id),
            })
    return out
