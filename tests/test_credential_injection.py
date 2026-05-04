"""Credential injection tests — verify the broker injects correct auth headers.

Uses simulate mode (X-Jentic-Simulate: true) to inspect injected headers
without making real upstream calls. Covers bearer, basic, apiKey (header),
and compound (Secret + Identity) two-header auth schemes.
"""

import asyncio
import json
import os

import aiosqlite
import pytest
from src import vault


BEARER_HOST = "127.0.10.1"
BASIC_HOST = "127.0.10.2"
APIKEY_HOST = "127.0.10.3"
COMPOUND_HOST = "127.0.10.4"


@pytest.fixture(scope="module")
def injection_credentials(admin_client, agent_key_header):
    """Set up credentials with different auth types, scheme blobs, and routes."""

    async def setup():
        db_path = os.environ["DB_PATH"]

        creds = [
            {
                "id": "inject-bearer",
                "label": "Bearer Token",
                "value": "my-secret-bearer-token",
                "api_id": BEARER_HOST,
                "auth_type": "bearer",
                "scheme": json.dumps(
                    {"in": "header", "name": "Authorization", "prefix": "Bearer "}
                ),
                "host": BEARER_HOST,
            },
            {
                "id": "inject-basic",
                "label": "Basic Auth",
                "value": "my-password",
                "api_id": BASIC_HOST,
                "auth_type": "basic",
                "identity": "myuser",
                "scheme": json.dumps(
                    {
                        "in": "header",
                        "name": "Authorization",
                        "prefix": "Basic ",
                        "encode": "base64",
                    }
                ),
                "host": BASIC_HOST,
            },
            {
                "id": "inject-apikey",
                "label": "API Key Header",
                "value": "sk-my-api-key-12345",
                "api_id": APIKEY_HOST,
                "auth_type": "apiKey",
                "scheme": json.dumps({"in": "header", "name": "X-Api-Key"}),
                "host": APIKEY_HOST,
            },
            {
                "id": "inject-compound",
                "label": "Compound Auth",
                "value": "compound-secret-key",
                "api_id": COMPOUND_HOST,
                "auth_type": "apiKey",
                "identity": "admin-user",
                "scheme": json.dumps(
                    {
                        "secret": {"in": "header", "name": "Api-Key"},
                        "identity": {"in": "header", "name": "Api-Username"},
                    }
                ),
                "host": COMPOUND_HOST,
            },
        ]

        async with aiosqlite.connect(db_path) as db:
            for c in creds:
                enc = vault.encrypt(c["value"])
                await db.execute(
                    "INSERT OR IGNORE INTO credentials "
                    "(id, label, env_var, encrypted_value, api_id, auth_type, identity, scheme) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        c["id"],
                        c["label"],
                        c["id"].upper().replace("-", "_"),
                        enc,
                        c["api_id"],
                        c["auth_type"],
                        c.get("identity"),
                        c.get("scheme"),
                    ),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO credential_routes (credential_id, host) VALUES (?, ?)",
                    (c["id"], c["host"]),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO toolkit_credentials (toolkit_id, credential_id) VALUES ('default', ?)",
                    (c["id"],),
                )
            await db.commit()

    asyncio.run(setup())
    yield

    async def teardown():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            for cid in ("inject-bearer", "inject-basic", "inject-apikey", "inject-compound"):
                await db.execute("DELETE FROM credential_routes WHERE credential_id=?", (cid,))
                await db.execute("DELETE FROM toolkit_credentials WHERE credential_id=?", (cid,))
                await db.execute("DELETE FROM credentials WHERE id=?", (cid,))
            await db.commit()

    asyncio.run(teardown())


def _lower_keys(d: dict) -> dict:
    """Lowercase all keys for case-insensitive header comparison."""
    return {k.lower(): v for k, v in d.items()}


def test_bearer_token_injection(client, agent_key_header, injection_credentials):
    """Bearer credential should inject Authorization header (masked in simulate)."""
    resp = client.get(
        f"/{BEARER_HOST}/api/test",
        headers={**agent_key_header, "X-Jentic-Simulate": "true"},
    )
    assert resp.status_code == 200, f"Simulate failed: {resp.text}"
    headers = _lower_keys(resp.json()["would_send"]["headers"])
    # Simulate mode masks Authorization with ***
    assert "authorization" in headers, f"Expected Authorization header, got: {list(headers.keys())}"
    assert headers["authorization"] == "***"


def test_basic_auth_injection(client, agent_key_header, injection_credentials):
    """Basic auth credential should inject Authorization header (masked in simulate)."""
    resp = client.get(
        f"/{BASIC_HOST}/api/test",
        headers={**agent_key_header, "X-Jentic-Simulate": "true"},
    )
    assert resp.status_code == 200, f"Simulate failed: {resp.text}"
    headers = _lower_keys(resp.json()["would_send"]["headers"])
    assert "authorization" in headers, f"Expected Authorization header, got: {list(headers.keys())}"
    assert headers["authorization"] == "***"


def test_apikey_header_injection(client, agent_key_header, injection_credentials):
    """apiKey credential should inject the custom header with the value."""
    resp = client.get(
        f"/{APIKEY_HOST}/api/test",
        headers={**agent_key_header, "X-Jentic-Simulate": "true"},
    )
    assert resp.status_code == 200, f"Simulate failed: {resp.text}"
    headers = _lower_keys(resp.json()["would_send"]["headers"])
    assert "x-api-key" in headers, f"Expected X-Api-Key header, got: {list(headers.keys())}"
    assert headers["x-api-key"] == "sk-my-api-key-12345"


def test_compound_auth_injection(client, agent_key_header, injection_credentials):
    """Compound credential should inject both Secret and Identity headers."""
    resp = client.get(
        f"/{COMPOUND_HOST}/api/test",
        headers={**agent_key_header, "X-Jentic-Simulate": "true"},
    )
    assert resp.status_code == 200, f"Simulate failed: {resp.text}"
    headers = _lower_keys(resp.json()["would_send"]["headers"])
    assert "api-key" in headers, f"Expected Api-Key header, got: {list(headers.keys())}"
    assert headers["api-key"] == "compound-secret-key"
    assert "api-username" in headers, f"Expected Api-Username header, got: {list(headers.keys())}"
    assert headers["api-username"] == "admin-user"
