"""Server URL resolution tests — verify broker uses correct scheme for .local hosts.

Uses simulate mode (X-Jentic-Simulate: true) to inspect the upstream URL the
broker would construct, without making a real upstream call.

Regression test for issue where the resolved scheme from server_variables was
discarded and re-inferred from port heuristics — broke HTTPS on default port 443.
"""

import asyncio
import json
import os

import aiosqlite
import pytest
from src import vault


HTTPS_API_ID = "https-local.local"
HTTP_API_ID = "http-local.local"


@pytest.fixture(scope="module")
def local_apis_with_credentials(client, admin_client, agent_key_header):
    """Register two .local APIs (https + http templates) with credentials and routes."""

    async def setup():
        db_path = os.environ["DB_PATH"]
        specs_dir = os.path.join(os.path.dirname(db_path), "specs")
        os.makedirs(specs_dir, exist_ok=True)

        # HTTPS template API (e.g. Portainer on https://{host})
        https_spec = {
            "openapi": "3.0.3",
            "info": {"title": "HTTPS Local API", "version": "1.0"},
            "servers": [
                {"url": "https://{host}", "variables": {"host": {"default": "localhost:9443"}}}
            ],
            "components": {"securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer"}}},
            "paths": {
                "/api": {
                    "get": {"operationId": "test", "responses": {"200": {"description": "ok"}}}
                }
            },
        }
        https_path = os.path.join(specs_dir, "https_local.json")
        with open(https_path, "w") as f:
            json.dump(https_spec, f)

        # HTTP template API (e.g. Home Assistant on http://{host})
        http_spec = {
            "openapi": "3.0.3",
            "info": {"title": "HTTP Local API", "version": "1.0"},
            "servers": [
                {"url": "http://{host}", "variables": {"host": {"default": "localhost:8123"}}}
            ],
            "components": {"securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer"}}},
            "paths": {
                "/api": {
                    "get": {"operationId": "test", "responses": {"200": {"description": "ok"}}}
                }
            },
        }
        http_path = os.path.join(specs_dir, "http_local.json")
        with open(http_path, "w") as f:
            json.dump(http_spec, f)

        enc = vault.encrypt("fake-token")
        async with aiosqlite.connect(db_path) as db:
            # Register APIs
            await db.execute(
                "INSERT OR IGNORE INTO apis (id, name, base_url, spec_path) VALUES (?, ?, ?, ?)",
                (HTTPS_API_ID, "HTTPS Local", "https://{host}", https_path),
            )
            await db.execute(
                "INSERT OR IGNORE INTO apis (id, name, base_url, spec_path) VALUES (?, ?, ?, ?)",
                (HTTP_API_ID, "HTTP Local", "http://{host}", http_path),
            )

            # Create credentials with server_variables
            await db.execute(
                "INSERT OR IGNORE INTO credentials "
                "(id, label, env_var, encrypted_value, api_id, auth_type, server_variables, scheme) "
                "VALUES (?, ?, ?, ?, ?, 'bearer', ?, ?)",
                (
                    "https-local-cred",
                    "HTTPS Local Token",
                    "HTTPS_LOCAL",
                    enc,
                    HTTPS_API_ID,
                    json.dumps({"host": "10.0.0.2"}),
                    json.dumps({"in": "header", "name": "Authorization", "prefix": "Bearer "}),
                ),
            )
            await db.execute(
                "INSERT OR IGNORE INTO credentials "
                "(id, label, env_var, encrypted_value, api_id, auth_type, server_variables, scheme) "
                "VALUES (?, ?, ?, ?, ?, 'bearer', ?, ?)",
                (
                    "http-local-cred",
                    "HTTP Local Token",
                    "HTTP_LOCAL",
                    enc,
                    HTTP_API_ID,
                    json.dumps({"host": "192.168.1.50:8123"}),
                    json.dumps({"in": "header", "name": "Authorization", "prefix": "Bearer "}),
                ),
            )

            # Create routes
            await db.execute(
                "INSERT OR IGNORE INTO credential_routes (credential_id, host) VALUES (?, ?)",
                ("https-local-cred", HTTPS_API_ID),
            )
            await db.execute(
                "INSERT OR IGNORE INTO credential_routes (credential_id, host) VALUES (?, ?)",
                ("http-local-cred", HTTP_API_ID),
            )

            # Bind to default toolkit
            await db.execute(
                "INSERT OR IGNORE INTO toolkit_credentials (toolkit_id, credential_id) VALUES ('default', 'https-local-cred')",
            )
            await db.execute(
                "INSERT OR IGNORE INTO toolkit_credentials (toolkit_id, credential_id) VALUES ('default', 'http-local-cred')",
            )
            await db.commit()

    asyncio.run(setup())
    yield

    async def teardown():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            for cid in ("https-local-cred", "http-local-cred"):
                await db.execute("DELETE FROM credential_routes WHERE credential_id=?", (cid,))
                await db.execute("DELETE FROM toolkit_credentials WHERE credential_id=?", (cid,))
                await db.execute("DELETE FROM credentials WHERE id=?", (cid,))
            for aid in (HTTPS_API_ID, HTTP_API_ID):
                await db.execute("DELETE FROM apis WHERE id=?", (aid,))
            await db.commit()

    asyncio.run(teardown())


def test_broker_uses_https_for_https_template(
    client, agent_key_header, local_apis_with_credentials
):
    """Broker should use https:// when the spec's server URL template is https://{host}.

    Regression: previously the scheme was discarded and re-inferred from port.
    For 10.0.0.2 (no explicit port, private IP), the heuristic chose HTTP.
    """
    resp = client.get(
        f"/{HTTPS_API_ID}/api",
        headers={**agent_key_header, "X-Jentic-Simulate": "true"},
    )
    assert resp.status_code == 200, f"Simulate failed: {resp.text}"
    data = resp.json()
    url = data["would_send"]["url"]
    assert url.startswith("https://"), f"Expected https:// upstream URL, got: {url}"
    assert "10.0.0.2" in url, f"Expected resolved host in URL, got: {url}"


def test_broker_uses_http_for_http_template(client, agent_key_header, local_apis_with_credentials):
    """Broker should use http:// when the spec's server URL template is http://{host}."""
    resp = client.get(
        f"/{HTTP_API_ID}/api",
        headers={**agent_key_header, "X-Jentic-Simulate": "true"},
    )
    assert resp.status_code == 200, f"Simulate failed: {resp.text}"
    data = resp.json()
    url = data["would_send"]["url"]
    assert url.startswith("http://"), f"Expected http:// upstream URL, got: {url}"
    assert "192.168.1.50:8123" in url, f"Expected resolved host in URL, got: {url}"
