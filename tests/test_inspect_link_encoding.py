"""Inspect link URL encoding tests.

Verifies that GET /inspect/{capability_id} returns a properly percent-encoded
`_links.self` for operation and workflow capabilities (IDs contain '/').
"""

import asyncio
import json
import os
from pathlib import Path
from urllib.parse import quote

import aiosqlite
import pytest
from src.config import JENTIC_PUBLIC_HOSTNAME


API_ID = "api.link-encoding-test.io"
JENTIC_ID = f"GET/{API_ID}/v1/items"
ENCODED_JENTIC_ID = quote(JENTIC_ID, safe="")


@pytest.fixture(scope="module")
def imported_workflow(admin_client):
    """Import the test workflow fixture once for the module."""
    workflow_path = Path(__file__).parent / "fixtures" / "test-workflow.arazzo.json"
    assert workflow_path.exists(), f"Test workflow fixture not found: {workflow_path}"

    resp = admin_client.post(
        "/import",
        json={"sources": [{"type": "path", "path": str(workflow_path)}]},
    )
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    result = resp.json()
    assert result["succeeded"] > 0, "Expected at least one workflow to be imported"
    return result


@pytest.fixture(scope="module")
def inspect_link_api(client, agent_key_header):
    """Register a minimal operation so /inspect/{id} can resolve it."""

    async def setup():
        db_path = os.environ["DB_PATH"]
        specs_dir = os.path.join(os.path.dirname(db_path), "specs")
        os.makedirs(specs_dir, exist_ok=True)

        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Link Encoding Test API", "version": "1.0"},
            "servers": [{"url": f"https://{API_ID}"}],
            "paths": {
                "/v1/items": {
                    "get": {
                        "operationId": "listItems",
                        "summary": "List items",
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            },
        }
        spec_path = os.path.join(specs_dir, f"{API_ID}.json")
        with open(spec_path, "w") as f:
            json.dump(spec, f)

        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO apis (id, name, base_url, spec_path) VALUES (?, ?, ?, ?)",
                (API_ID, "Link Encoding Test API", f"https://{API_ID}", spec_path),
            )
            await db.execute(
                "INSERT OR IGNORE INTO operations "
                "(id, api_id, operation_id, jentic_id, method, path, summary) "
                "VALUES (?, ?, ?, ?, 'GET', '/v1/items', 'List items')",
                (f"op-{API_ID}", API_ID, "listItems", JENTIC_ID),
            )
            await db.commit()

    asyncio.run(setup())
    yield

    async def teardown():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            await db.execute("DELETE FROM operations WHERE api_id=?", (API_ID,))
            await db.execute("DELETE FROM apis WHERE id=?", (API_ID,))
            await db.commit()

    asyncio.run(teardown())


def test_operation_inspect_self_link_is_url_encoded(client, agent_key_header, inspect_link_api):
    """_links.self for an operation capability must be percent-encoded.

    Capability IDs contain '/' (e.g. GET/host/path). The self link must
    encode these so clients can round-trip to /inspect/{encoded_id}.
    """
    resp = client.get(f"/inspect/{JENTIC_ID}", headers=agent_key_header)
    assert resp.status_code == 200, f"Inspect failed: {resp.text}"

    data = resp.json()
    self_link = data.get("_links", {}).get("self")
    assert self_link is not None, "_links.self missing from response"
    assert self_link == f"/inspect/{ENCODED_JENTIC_ID}", (
        f"Expected encoded self link '/inspect/{ENCODED_JENTIC_ID}', got '{self_link}'"
    )


def test_workflow_inspect_self_link_is_url_encoded(admin_client, imported_workflow):
    """_links.self for a workflow capability must stay percent-encoded (regression)."""
    assert imported_workflow["status"] == "ok"
    capability_id = f"POST/{JENTIC_PUBLIC_HOSTNAME}/workflows/test-workflow"
    encoded_id = quote(capability_id, safe="")

    resp = admin_client.get(f"/inspect/{capability_id}")
    assert resp.status_code == 200, f"Inspect workflow failed: {resp.text}"

    self_link = resp.json().get("_links", {}).get("self")
    assert self_link is not None, "_links.self missing from response"
    assert self_link == f"/inspect/{encoded_id}", (
        f"Expected encoded self link '/inspect/{encoded_id}', got '{self_link}'"
    )
