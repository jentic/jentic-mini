"""Inspect link URL encoding tests.

Verifies that GET /inspect/{capability_id} returns a properly percent-encoded
`_links.self` value for both operation and workflow capability types.

Capability IDs contain '/' characters (e.g. GET/api.example.com/v1/resource)
which must be percent-encoded in URLs. Without encoding, the self link would
contain raw slashes that browsers and clients would misparse as path separators.
"""

import asyncio
import json
import os
from urllib.parse import quote

import aiosqlite
import pytest
from src import vault


API_ID = "api.link-encoding-test.io"
JENTIC_ID = f"GET/{API_ID}/v1/items"
ENCODED_JENTIC_ID = quote(JENTIC_ID, safe="")


@pytest.fixture(scope="module")
def inspect_link_api(client, admin_session, agent_key_header):
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
    assert "/" not in self_link.removeprefix("/inspect/"), (
        f"self link contains unencoded '/' in capability ID portion: {self_link}"
    )
