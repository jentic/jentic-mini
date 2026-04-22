"""Capability inspect server_variables_configured tests.

Verifies that GET /inspect/{id} returns server_variables_configured from
the credential matching the capability's api_id — not from an unrelated
credential in the same toolkit.
"""

import asyncio
import json
import os

import aiosqlite
import pytest
from src import vault


API_A = "portainer.local"
API_B = "discourse.local"
SV_A = {"host": "10.0.0.2:9443"}
SV_B = {"host": "forum.acme.com"}


@pytest.fixture(scope="module")
def two_local_apis(client, admin_session, agent_key_header):
    """Register two .local APIs with different server_variables on their credentials."""

    async def setup():
        db_path = os.environ["DB_PATH"]
        specs_dir = os.path.join(os.path.dirname(db_path), "specs")
        os.makedirs(specs_dir, exist_ok=True)

        for api_id, title, sv, cred_id in [
            (API_A, "Portainer", SV_A, "cred-portainer"),
            (API_B, "Discourse", SV_B, "cred-discourse"),
        ]:
            spec = {
                "openapi": "3.0.3",
                "info": {"title": title, "version": "1.0"},
                "servers": [
                    {"url": "https://{host}", "variables": {"host": {"default": "localhost"}}}
                ],
                "components": {
                    "securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer"}}
                },
                "paths": {
                    "/api/test": {
                        "get": {
                            "operationId": f"{api_id}-test",
                            "responses": {"200": {"description": "ok"}},
                        }
                    }
                },
            }
            spec_path = os.path.join(specs_dir, f"{api_id}.json")
            with open(spec_path, "w") as f:
                json.dump(spec, f)

            enc = vault.encrypt("fake-token")
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO apis (id, name, base_url, spec_path) VALUES (?, ?, ?, ?)",
                    (api_id, title, "https://{host}", spec_path),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO credentials "
                    "(id, label, env_var, encrypted_value, api_id, auth_type, server_variables) "
                    "VALUES (?, ?, ?, ?, ?, 'bearer', ?)",
                    (cred_id, f"{title} Token", cred_id.upper(), enc, api_id, json.dumps(sv)),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO credential_routes (credential_id, host) VALUES (?, ?)",
                    (cred_id, api_id),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO toolkit_credentials (toolkit_id, credential_id) VALUES ('default', ?)",
                    (cred_id,),
                )
                # Register the operation
                await db.execute(
                    "INSERT OR IGNORE INTO operations (id, api_id, operation_id, jentic_id, method, path, summary) "
                    "VALUES (?, ?, ?, ?, 'GET', '/api/test', ?)",
                    (
                        f"op-{api_id}",
                        api_id,
                        f"{api_id}-test",
                        f"GET/{api_id}/api/test",
                        f"{title} test",
                    ),
                )
                await db.commit()

    asyncio.run(setup())
    yield

    async def teardown():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            for cred_id in ("cred-portainer", "cred-discourse"):
                await db.execute("DELETE FROM credential_routes WHERE credential_id=?", (cred_id,))
                await db.execute(
                    "DELETE FROM toolkit_credentials WHERE credential_id=?", (cred_id,)
                )
                await db.execute("DELETE FROM credentials WHERE id=?", (cred_id,))
            for api_id in (API_A, API_B):
                await db.execute("DELETE FROM operations WHERE api_id=?", (api_id,))
                await db.execute("DELETE FROM apis WHERE id=?", (api_id,))
            await db.commit()

    asyncio.run(teardown())


def test_inspect_shows_correct_server_vars_for_portainer(client, agent_key_header, two_local_apis):
    """Inspecting a Portainer operation should show Portainer's server_variables, not Discourse's."""
    resp = client.get(f"/inspect/GET/{API_A}/api/test?toolkit_id=default", headers=agent_key_header)
    assert resp.status_code == 200, f"Inspect failed: {resp.text}"
    data = resp.json()
    creds = data.get("credentials", {})
    assert creds.get("status") == "configured", f"Expected configured credentials, got: {creds}"
    assert creds.get("server_variables_configured") == SV_A, (
        f"Expected Portainer vars {SV_A}, got {creds.get('server_variables_configured')}"
    )


def test_inspect_shows_correct_server_vars_for_discourse(client, agent_key_header, two_local_apis):
    """Inspecting a Discourse operation should show Discourse's server_variables, not Portainer's."""
    resp = client.get(f"/inspect/GET/{API_B}/api/test?toolkit_id=default", headers=agent_key_header)
    assert resp.status_code == 200, f"Inspect failed: {resp.text}"
    data = resp.json()
    creds = data.get("credentials", {})
    assert creds.get("status") == "configured", f"Expected configured credentials, got: {creds}"
    assert creds.get("server_variables_configured") == SV_B, (
        f"Expected Discourse vars {SV_B}, got {creds.get('server_variables_configured')}"
    )
