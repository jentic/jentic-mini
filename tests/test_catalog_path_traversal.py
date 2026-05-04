"""Regression test for the py/path-injection finding at catalog.py.

Feeds `lazy_import_catalog_workflows` a crafted Arazzo document whose
`workflowId` contains path-traversal sequences. Asserts that no file is
written outside `WORKFLOWS_DIR` and the traversal branch actually runs
(so the assertion is not a false negative from an early error).
"""

import asyncio
import json
import shutil
from io import BytesIO
from unittest.mock import patch

import aiosqlite
from src.config import DB_PATH, WORKFLOWS_DIR
from src.routers.catalog import WORKFLOW_MANIFEST_PATH, lazy_import_catalog_workflows


API_ID = "api.traversal-test.example"


def _fake_urlopen_factory(doc: dict):
    def _fake(*_args, **_kwargs):
        return BytesIO(json.dumps(doc).encode())

    return _fake


async def _insert_api_row() -> None:
    """Insert a row in `apis` so sourceDescriptions rewriting branch runs."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO apis (id, name, spec_path) VALUES (?, ?, ?)",
            (API_ID, "Traversal Test", "/tmp/fake-spec.json"),
        )
        await db.commit()


async def _cleanup_api_row() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM apis WHERE id=?", (API_ID,))
        await db.commit()


def test_malicious_workflow_id_cannot_escape_workflows_dir(client):
    """A traversal-laden workflowId must not create files outside WORKFLOWS_DIR.

    The `client` fixture ensures the app lifespan has run and the schema
    exists, even though we hit the function directly.
    """
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    workflows_root = WORKFLOWS_DIR.resolve()
    before = set(workflows_root.rglob("*"))

    # Snapshot the workflow manifest so we can restore it — some earlier
    # tests may have written entries we must not destroy.
    prior_manifest = WORKFLOW_MANIFEST_PATH.read_text() if WORKFLOW_MANIFEST_PATH.exists() else None

    source_id = API_ID.replace("/", "~", 1)
    WORKFLOW_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WORKFLOW_MANIFEST_PATH.write_text(
        json.dumps([{"source_id": source_id, "path": f"workflows/{source_id}", "api_id": API_ID}])
    )

    # A benign workflowId alongside the malicious ones proves the traversal
    # branch actually executes end-to-end (rather than erroring out early and
    # silently passing the containment assertion).
    arazzo_doc = {
        "arazzo": "1.0.0",
        "info": {"title": "Traversal", "version": "1.0"},
        "sourceDescriptions": [{"name": "self", "url": "./openapi.json", "type": "openapi"}],
        "workflows": [
            {"workflowId": "benign-canary", "steps": []},
            {"workflowId": "../../../../etc/passwd", "steps": []},
            {"workflowId": "..%2F..%2Fescaped", "steps": []},
        ],
    }

    new_files: set = set()
    slugs: list[str] = []
    try:
        asyncio.run(_insert_api_row())
        with patch("urllib.request.urlopen", _fake_urlopen_factory(arazzo_doc)):
            slugs = asyncio.run(lazy_import_catalog_workflows(API_ID))

        after = set(workflows_root.rglob("*"))
        new_files = after - before

        # Sanity: the benign workflow must have produced at least one file,
        # proving the code actually reached the open() sink.
        assert len(new_files) >= 1, "expected at least the benign workflow to be written"

        # Every new artefact must be contained inside WORKFLOWS_DIR.
        for p in new_files:
            resolved = p.resolve()
            assert resolved.is_relative_to(workflows_root), (
                f"Path escaped WORKFLOWS_DIR: {resolved} (root={workflows_root})"
            )

        # Filenames must match the sanitised pattern — no raw traversal tokens.
        for p in new_files:
            assert ".." not in p.name
            assert "/" not in p.name
            assert "\\" not in p.name

        # The benign slug must be present (proves the code path ran). Any
        # slugs derived from the malicious inputs must be fully sanitised —
        # no traversal tokens surviving.
        assert "benign-canary" in slugs, f"benign slug missing, got: {slugs}"
        for s in slugs:
            assert ".." not in s
            assert "/" not in s
            assert "\\" not in s
    finally:
        # Restore (or remove) the manifest so other tests aren't affected.
        if prior_manifest is None:
            WORKFLOW_MANIFEST_PATH.unlink(missing_ok=True)
        else:
            WORKFLOW_MANIFEST_PATH.write_text(prior_manifest)

        # Clean up anything written so repeated runs don't accumulate files
        # or poison the shared workflow index.
        for p in sorted(new_files, reverse=True):
            if p.is_file():
                p.unlink(missing_ok=True)
            elif p.is_dir():
                shutil.rmtree(p, ignore_errors=True)

        asyncio.run(_cleanup_api_row())
        asyncio.run(_cleanup_workflow_rows(slugs))


async def _cleanup_workflow_rows(slugs: list[str]) -> None:
    """Remove workflow rows we registered during the test."""
    async with aiosqlite.connect(DB_PATH) as db:
        for s in slugs:
            await db.execute("DELETE FROM workflows WHERE slug=?", (s,))
        await db.commit()
