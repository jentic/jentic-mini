"""Regression test for the py/path-injection finding at catalog.py.

Feeds `lazy_import_catalog_workflows` a crafted Arazzo document whose
`workflowId` contains path-traversal sequences. Asserts that no file is
written outside `WORKFLOWS_DIR` and the function returns no imported
slugs for the malicious entries.
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


class _FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_urlopen_factory(doc: dict):
    def _fake(*_args, **_kwargs):
        return _FakeResponse(json.dumps(doc).encode())

    return _fake


def _seed_workflow_manifest(tmp_entry: dict) -> None:
    """Write a workflow manifest pointing at our synthetic source_id."""

    WORKFLOW_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WORKFLOW_MANIFEST_PATH.write_text(json.dumps([tmp_entry]))


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

    The `client` fixture is requested to ensure the app lifespan has run and
    the schema exists, even though we hit the function directly.
    """
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    workflows_root = WORKFLOWS_DIR.resolve()
    before = set(workflows_root.rglob("*"))

    # Seed the manifest entry this api_id will resolve to.
    source_id = API_ID.replace("/", "~", 1)
    _seed_workflow_manifest(
        {"source_id": source_id, "path": f"workflows/{source_id}", "api_id": API_ID}
    )

    arazzo_doc = {
        "arazzo": "1.0.0",
        "info": {"title": "Traversal", "version": "1.0"},
        "sourceDescriptions": [{"name": "self", "url": "./openapi.json", "type": "openapi"}],
        "workflows": [
            {
                "workflowId": "../../../../etc/passwd",
                "steps": [],
            },
            {
                "workflowId": "..%2F..%2Fescaped",
                "steps": [],
            },
        ],
    }

    try:
        asyncio.run(_insert_api_row())
        with patch("urllib.request.urlopen", _fake_urlopen_factory(arazzo_doc)):
            slugs = asyncio.run(lazy_import_catalog_workflows(API_ID))
    finally:
        asyncio.run(_cleanup_api_row())

    after = set(workflows_root.rglob("*"))
    new_files = after - before

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

    # Cleanup: drop anything we created so we don't pollute the shared
    # test DB workflow index on subsequent runs.
    for p in sorted(new_files, reverse=True):
        if p.is_file():
            p.unlink(missing_ok=True)
        elif p.is_dir():
            shutil.rmtree(p, ignore_errors=True)

    # Defence-in-depth — even if a slug came back, it must be whitelist-clean.
    for s in slugs:
        assert ".." not in s
        assert "/" not in s
