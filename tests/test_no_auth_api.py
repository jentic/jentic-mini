"""No-auth API passthrough tests — broker should forward without credentials
when the API spec has no securitySchemes, and block when it does.

Covers issue #48: importing a no-auth API spec should not break broker calls.
"""
import asyncio
import json
import os

import aiosqlite
import pytest


NO_AUTH_HOST = "127.0.0.3"
AUTH_HOST = "127.0.0.4"


@pytest.fixture(scope="module")
def registered_apis(client, admin_session):
    """Register two APIs: one without security schemes, one with."""

    async def setup():
        db_path = os.environ["DB_PATH"]
        specs_dir = os.path.join(os.path.dirname(db_path), "specs")
        os.makedirs(specs_dir, exist_ok=True)

        # No-auth spec (no securitySchemes)
        no_auth_spec = {
            "openapi": "3.0.3",
            "info": {"title": "No-Auth API", "version": "1.0"},
            "paths": {
                "/get": {
                    "get": {"operationId": "getStuff", "responses": {"200": {"description": "OK"}}}
                }
            },
        }
        no_auth_path = os.path.join(specs_dir, "no_auth_api.json")
        with open(no_auth_path, "w") as f:
            json.dump(no_auth_spec, f)

        # Auth spec (has securitySchemes)
        auth_spec = {
            "openapi": "3.0.3",
            "info": {"title": "Auth API", "version": "1.0"},
            "components": {
                "securitySchemes": {
                    "BearerAuth": {"type": "http", "scheme": "bearer"}
                }
            },
            "security": [{"BearerAuth": []}],
            "paths": {
                "/data": {
                    "get": {"operationId": "getData", "responses": {"200": {"description": "OK"}}}
                }
            },
        }
        auth_path = os.path.join(specs_dir, "auth_api.json")
        with open(auth_path, "w") as f:
            json.dump(auth_spec, f)

        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO apis (id, name, base_url, spec_path) VALUES (?, ?, ?, ?)",
                (NO_AUTH_HOST, "No-Auth API", f"https://{NO_AUTH_HOST}", no_auth_path),
            )
            await db.execute(
                "INSERT OR IGNORE INTO apis (id, name, base_url, spec_path) VALUES (?, ?, ?, ?)",
                (AUTH_HOST, "Auth API", f"https://{AUTH_HOST}", auth_path),
            )
            await db.commit()

    asyncio.run(setup())


def test_no_auth_api_forwards_without_credentials(client, agent_key_header, registered_apis):
    """A registered API with no securitySchemes should not require credentials."""
    resp = client.get(f"/{NO_AUTH_HOST}/get", headers=agent_key_header)
    # The upstream is non-routable so we expect a connection error (502 or 504),
    # NOT a credential lookup error (500).
    assert resp.status_code in (502, 504), f"Expected 502/504 (upstream unreachable), got {resp.status_code}: {resp.text}"


def test_auth_api_requires_credentials(client, agent_key_header, registered_apis):
    """A registered API with securitySchemes should fail without credentials."""
    resp = client.get(f"/{AUTH_HOST}/data", headers=agent_key_header)
    assert resp.status_code == 500
    body = resp.json()
    assert "CREDENTIAL_LOOKUP_FAILED" in body.get("error", "")
