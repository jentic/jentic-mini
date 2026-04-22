"""Verify that broker credential injection requires X-Jentic-API-Key.

Workflow execution routes HTTP calls through the broker via a requests.Session
that includes the caller's API key. Without the key, broker requests are
anonymous and credentials are not injected — upstream APIs would fail auth.

This test ensures the broker correctly distinguishes authenticated from
anonymous requests, validating the session header injection used by
arazzo-runner workflow execution.
"""
import asyncio
import json
import os

import aiosqlite
import pytest

from src import vault

WORKFLOW_AUTH_HOST = "127.0.10.50"


@pytest.fixture(scope="module")
def workflow_auth_credential(client, admin_session, agent_key_header):
    """Set up a credential to test auth vs anonymous broker paths."""

    async def setup():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            enc = vault.encrypt("wf-test-secret-key")
            await db.execute(
                "INSERT OR IGNORE INTO credentials "
                "(id, label, env_var, encrypted_value, api_id, auth_type, scheme) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("wf-auth-test", "Workflow Auth Test", "WF_AUTH_TEST",
                 enc, WORKFLOW_AUTH_HOST, "apiKey",
                 json.dumps({"in": "header", "name": "X-Api-Key"})),
            )
            await db.execute(
                "INSERT OR IGNORE INTO credential_routes (credential_id, host) VALUES (?, ?)",
                ("wf-auth-test", WORKFLOW_AUTH_HOST),
            )
            await db.execute(
                "INSERT OR IGNORE INTO toolkit_credentials (toolkit_id, credential_id) VALUES ('default', ?)",
                ("wf-auth-test",),
            )
            await db.commit()

    asyncio.run(setup())
    yield

    async def teardown():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            await db.execute("DELETE FROM credential_routes WHERE credential_id='wf-auth-test'")
            await db.execute("DELETE FROM toolkit_credentials WHERE credential_id='wf-auth-test'")
            await db.execute("DELETE FROM credentials WHERE id='wf-auth-test'")
            await db.commit()

    asyncio.run(teardown())


def test_broker_injects_credentials_with_api_key(client, agent_key_header, workflow_auth_credential):
    """Broker injects credentials when X-Jentic-API-Key is present (authenticated path)."""
    resp = client.get(
        f"/{WORKFLOW_AUTH_HOST}/api/test",
        headers={**agent_key_header, "X-Jentic-Simulate": "true"},
    )
    assert resp.status_code == 200, f"Simulate failed: {resp.text}"
    body = resp.json()
    headers = {k.lower(): v for k, v in body["would_send"]["headers"].items()}
    assert "x-api-key" in headers, f"Expected credential injection, got headers: {list(headers.keys())}"
    assert headers["x-api-key"] == "wf-test-secret-key"


def test_broker_skips_credentials_without_api_key(workflow_auth_credential):
    """Broker skips credential injection when no X-Jentic-API-Key is present (anonymous path).

    This is the path arazzo-runner subprocess requests took before the
    session header fix — requests went through the broker but without
    an API key, so no toolkit was resolved and credentials were not injected.

    Uses a fresh client to avoid session cookie leakage.
    """
    from starlette.testclient import TestClient
    from src.main import app
    with TestClient(app, raise_server_exceptions=False) as anon_client:
        resp = anon_client.get(
            f"/{WORKFLOW_AUTH_HOST}/api/test",
            headers={"X-Jentic-Simulate": "true"},
        )
    assert resp.status_code == 200, f"Simulate failed: {resp.text}"
    body = resp.json()
    headers = {k.lower(): v for k, v in body["would_send"]["headers"].items()}
    assert "x-api-key" not in headers, (
        f"Expected NO credential injection for anonymous request, but got x-api-key in headers"
    )
