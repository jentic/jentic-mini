"""
POST /import — unified intake for APIs (OpenAPI) and workflows (Arazzo).

Source types:
  - type: "path"   — local file path already on disk (admin)
  - type: "url"    — fetch spec from a remote URL
  - type: "inline" — spec content posted directly in the request

Detects whether the spec is an OpenAPI or Arazzo document and routes accordingly.
Synchronous (no job queue) — suitable for Jentic's local deployment.
"""
import json
import re
import uuid
import os
import urllib.request
import urllib.error
import yaml
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.validators import NormModel, NormStr

from src.db import get_db
from src.bm25 import get_index
import src.vault as vault
from src.models import ImportOut

router = APIRouter()

from src.config import JENTIC_PUBLIC_HOSTNAME, SPECS_DIR, WORKFLOWS_DIR
SPECS_DIR.mkdir(parents=True, exist_ok=True)
WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)


class ImportSource(NormModel):
    type: NormStr       # "path" | "url" | "inline"
    path: str | None = None
    url: str | None = None
    filename: str | None = None
    content: str | None = None
    force_api_id: str | None = None  # override derived api_id (e.g. catalog canonical ID)


class ImportRequest(NormModel):
    sources: list[ImportSource]


def _load_doc(source: ImportSource) -> tuple[dict, str | None]:
    """Load and parse a spec document. Returns (doc, saved_path)."""
    if source.type == "path":
        if not source.path:
            raise ValueError("path required for type=path")
        p = Path(source.path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {source.path}")
        raw = p.read_text()
        doc = yaml.safe_load(raw) if str(p).endswith((".yaml", ".yml")) else json.loads(raw)
        return doc, str(p)

    elif source.type == "url":
        if not source.url:
            raise ValueError("url required for type=url")
        req = urllib.request.Request(source.url, headers={"User-Agent": "Jentic/0.2"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        doc = yaml.safe_load(raw) if (source.url.endswith((".yaml", ".yml")) or raw.strip().startswith("openapi:") or raw.strip().startswith("arazzo:")) else json.loads(raw)
        # Save locally
        fname = source.filename or _url_to_filename(source.url)
        dest = SPECS_DIR / fname if not _is_arazzo(doc) else WORKFLOWS_DIR / fname
        dest.write_text(json.dumps(doc, ensure_ascii=False) if isinstance(raw, str) and raw.strip().startswith("{") else raw)
        return doc, str(dest)

    elif source.type == "inline":
        if not source.content:
            raise ValueError("content required for type=inline")
        raw = source.content
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError:
            doc = yaml.safe_load(raw)
        # Save locally
        fname = source.filename or f"inline_{uuid.uuid4().hex[:8]}.json"
        dest = SPECS_DIR / fname if not _is_arazzo(doc) else WORKFLOWS_DIR / fname
        dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2))
        return doc, str(dest)

    else:
        raise ValueError(f"Unknown source type: {source.type!r}")


def _is_arazzo(doc: dict) -> bool:
    return "arazzo" in doc


def _url_to_filename(url: str) -> str:
    # e.g. https://api.example.com/openapi.json -> api_example_com_openapi.json
    clean = re.sub(r"^https?://", "", url)
    clean = re.sub(r"[^a-zA-Z0-9._-]", "_", clean)
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean[:80] + ".json"


# ── OpenAPI registration ──────────────────────────────────────────────────────

async def _register_openapi(doc: dict, saved_path: str, force_api_id: str | None = None) -> dict:
    """Register an OpenAPI spec as an API + operations in Jentic."""
    # Import the heavy lifting from apis.py
    from src.routers.apis import (
        _load_base_url_from_spec, _derive_api_id, _parse_operations,
        _rebuild_index,
    )

    base_url = None
    servers = doc.get("servers", [])
    if servers:
        base_url = servers[0].get("url")

    api_id = force_api_id or (_derive_api_id(base_url) if base_url else None)
    if not api_id:
        title = doc.get("info", {}).get("title", "unknown")
        api_id = re.sub(r"[^a-z0-9]", "-", title.lower()).strip("-")[:40]

    # Allow caller to override the derived ID (e.g. catalog import uses canonical catalog api_id)
    if force_api_id:
        api_id = force_api_id

    name = doc.get("info", {}).get("title") or api_id
    description = doc.get("info", {}).get("description")

    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO apis (id, name, description, spec_path, base_url) VALUES (?,?,?,?,?)",
            (api_id, name, description, saved_path, base_url),
        )
        await db.commit()

    ops = _parse_operations(api_id, saved_path, base_url)
    async with get_db() as db:
        for op in ops:
            await db.execute(
                """INSERT OR REPLACE INTO operations
                   (id, api_id, operation_id, jentic_id, method, path, summary, description)
                   VALUES (:id, :api_id, :operation_id, :jentic_id, :method, :path, :summary, :description)""",
                op,
            )
        await db.commit()

    await _rebuild_index()

    # Auto-import catalog workflows when importing from catalog.
    # Note: POST /credentials also calls lazy_import_catalog_workflows as a safety net
    # for cases where the API was already registered (skipping _register_openapi).
    # Both calls are idempotent (upserts).
    workflows_imported = []
    if force_api_id:
        try:
            from src.routers.catalog import lazy_import_catalog_workflows
            workflows_imported = await lazy_import_catalog_workflows(api_id)
        except Exception as e:
            import logging
            logging.getLogger("jentic.import").warning("Workflow auto-import failed for '%s': %s", api_id, e)

    return {
        "type": "api",
        "id": api_id,
        "name": name,
        "operations_indexed": len(ops),
        "spec_path": saved_path,
        "workflows_imported": len(workflows_imported),
    }


# ── Arazzo registration ───────────────────────────────────────────────────────

async def _register_arazzo(doc: dict, saved_path: str, slug_hint: str | None = None) -> dict:
    """Register an Arazzo workflow file in Jentic."""
    import json as _json

    info = doc.get("info", {})
    workflows_list = doc.get("workflows", [])
    if not workflows_list:
        raise ValueError("Arazzo document contains no workflows")

    wf = workflows_list[0]
    workflow_id = wf.get("workflowId", "")
    name = wf.get("summary") or info.get("title") or workflow_id
    description = wf.get("description") or info.get("description")
    steps = wf.get("steps", [])
    steps_count = len(steps)

    # Derive involved API IDs from operationIds in steps
    involved_apis: list[str] = []
    for step in steps:
        op = step.get("operationId") or step.get("operationPath", "")
        # capability id format: METHOD/host/path → extract host
        m = re.match(r"^[A-Z]+/([^/]+)", op)
        if m:
            host = m.group(1)
            if host not in involved_apis:
                involved_apis.append(host)

    # Slug: prefer explicit hint, then workflowId, then filename
    if slug_hint:
        slug = slug_hint
    elif workflow_id:
        slug = re.sub(r"[^a-z0-9-]", "-", workflow_id.lower()).strip("-")[:60]
    else:
        slug = Path(saved_path).stem[:60]
    slug = re.sub(r"-+", "-", slug)

    input_schema = wf.get("inputs")

    async with get_db() as db:
        await db.execute(
            """INSERT OR REPLACE INTO workflows
               (slug, name, description, arazzo_path, input_schema, steps_count, involved_apis)
               VALUES (?,?,?,?,?,?,?)""",
            (
                slug, name, description, saved_path,
                _json.dumps(input_schema) if input_schema else None,
                steps_count,
                _json.dumps(involved_apis),
            ),
        )
        await db.commit()

    # Index in BM25
    index = get_index()
    index.add_workflow(slug, name, description, involved_apis)

    from src.routers.workflows import workflow_capability_id
    return {
        "type": "workflow",
        "id": workflow_capability_id(slug),
        "slug": slug,
        "name": name,
        "steps_count": steps_count,
        "arazzo_path": saved_path,
    }


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/import", summary="Import an API spec or workflow — add to the searchable catalog", response_model=ImportOut)
async def import_sources(body: ImportRequest):
    """Registers an OpenAPI spec or Arazzo workflow into the catalog and BM25 index.
    Source types: url (fetch from URL), upload (multipart file), inline (JSON body).
    For OpenAPI specs: parses operations, computes capability IDs, indexes descriptions.
    For Arazzo workflows: stores definition, extracts input schema and involved APIs.
    Returns the registered API or workflow with its canonical id.
    """
    results = []
    for i, source in enumerate(body.sources):
        try:
            doc, saved_path = _load_doc(source)
            if _is_arazzo(doc):
                result = await _register_arazzo(doc, saved_path)
            else:
                result = await _register_openapi(doc, saved_path, force_api_id=source.force_api_id)
            results.append({"index": i, "status": "success", **result})
        except Exception as e:
            results.append({
                "index": i,
                "status": "failed",
                "error": str(e),
                "source": source.model_dump(exclude_none=True),
            })

    succeeded = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - succeeded
    return {
        "status": "ok" if failed == 0 else ("partial" if succeeded > 0 else "failed"),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }
