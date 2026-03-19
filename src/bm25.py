"""In-memory BM25 index over registered operations AND workflows."""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from rank_bm25 import BM25Okapi

if TYPE_CHECKING:
    pass

_index: BM25Okapi | None = None
_docs: list[dict] = []   # Each doc has: type="operation"|"workflow", id, summary, description, ...


def _tokenise(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def build(operations: list[dict], workflows: list[dict] | None = None) -> None:
    """Rebuild the index from operations + workflows."""
    global _index, _docs
    # Tag type on each doc
    op_docs = [{**op, "type": "operation"} for op in operations]
    wf_docs = [{**wf, "type": "workflow"} for wf in (workflows or [])]
    _docs = op_docs + wf_docs

    corpus = []
    for doc in _docs:
        if doc["type"] == "operation":
            text = (
                f"{doc.get('summary','')} {doc.get('description','')} "
                f"{doc.get('path','')} {doc.get('method','')} "
                f"{doc.get('_vendor','')}"
            )
        else:  # workflow
            apis_text = " ".join(doc.get("involved_apis", []))
            text = (
                f"{doc.get('name','')} {doc.get('summary','')} "
                f"{doc.get('description','')} {apis_text}"
            )
        corpus.append(_tokenise(text))

    _index = BM25Okapi(corpus) if corpus else None


def get_index() -> "_BM25Index":
    """Return a handle for incremental additions (workflows added after build)."""
    return _BM25Index()


class _BM25Index:
    """Thin wrapper to allow adding a workflow doc and rebuilding."""
    def add_workflow(self, slug: str, name: str, description: str | None, involved_apis: list[str]):
        global _docs
        from src.routers.workflows import workflow_capability_id
        cap_id = workflow_capability_id(slug)
        # Avoid duplicates
        _docs = [d for d in _docs if not (d.get("type") == "workflow" and d.get("id") == cap_id)]
        _docs.append({
            "type": "workflow",
            "id": cap_id,
            "slug": slug,
            "name": name,
            "summary": name,
            "description": description,
            "involved_apis": involved_apis,
        })
        # Rebuild corpus
        corpus = []
        for doc in _docs:
            if doc["type"] == "operation":
                text = (
                    f"{doc.get('summary','')} {doc.get('description','')} "
                    f"{doc.get('path','')} {doc.get('method','')} "
                    f"{doc.get('_vendor','')}"
                )
            else:
                apis_text = " ".join(doc.get("involved_apis", []))
                text = (
                    f"{doc.get('name','')} {doc.get('summary','')} "
                    f"{doc.get('description','')} {apis_text}"
                )
            corpus.append(_tokenise(text))
        global _index
        _index = BM25Okapi(corpus) if corpus else None


def search(query: str, limit: int = 10) -> list[tuple[dict, float]]:
    """Return [(doc_dict, score), ...] sorted by score desc.

    Each doc has a 'type' field: 'operation' | 'workflow'.
    """
    if _index is None or not _docs:
        return []
    tokens = _tokenise(query)
    scores = _index.get_scores(tokens)
    ranked = sorted(zip(_docs, scores), key=lambda x: x[1], reverse=True)
    return [(doc, float(score)) for doc, score in ranked[:limit] if score > 0]
