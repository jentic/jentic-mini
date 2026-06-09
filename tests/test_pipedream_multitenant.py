"""Pipedream multi-tenant routing tests — issue #485.

Jira Cloud's catalog spec uses a templated base URL
(https://{your-domain}.atlassian.net). When connecting Jira via a Pipedream
OAuth broker the tenant ('your-domain') is collected at connect-link time,
carried through the connect-callback into oauth_broker_connect_labels, and must
end up:

  1. resolved into the credential's route host (acme.atlassian.net, not the
     literal {your-domain}.atlassian.net or the tenant-less atlassian.net), and
  2. persisted as server_variables on the pipedream_oauth credential so the
     broker can re-resolve the host at request time.

These tests drive the real discover_accounts() with the Pipedream HTTP layer
and catalog import mocked, then assert the resulting DB rows.
"""

import asyncio
import json
import os

import aiosqlite
import pytest
from src import vault
from src.brokers.pipedream import PipedreamOAuthBroker


BROKER_ID = "test-pd-jira-broker"
EXTERNAL_USER = "default"
JIRA_API_ID = "atlassian.net"
JIRA_BASE_URL = "https://{your-domain}.atlassian.net"
ACCOUNT_ID = "apn_jira_acme"


@pytest.fixture
def jira_pipedream_env(client, monkeypatch):
    """Seed a Jira-like API + a connect-label carrying the tenant, mock Pipedream IO."""

    db_path = os.environ["DB_PATH"]

    async def setup():
        specs_dir = os.path.join(os.path.dirname(db_path), "specs")
        os.makedirs(specs_dir, exist_ok=True)
        jira_spec = {
            "openapi": "3.0.1",
            "info": {"title": "The Jira Cloud platform REST API", "version": "1001.0.0"},
            "servers": [
                {
                    "url": JIRA_BASE_URL,
                    "variables": {"your-domain": {"description": "Your Atlassian domain name."}},
                }
            ],
            "components": {"securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer"}}},
            "paths": {
                "/rest/api/3/myself": {
                    "get": {"operationId": "getMyself", "responses": {"200": {"description": "ok"}}}
                }
            },
        }
        jira_path = os.path.join(specs_dir, "atlassian_net.json")
        with open(jira_path, "w") as f:
            json.dump(jira_spec, f)

        async with aiosqlite.connect(db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                "INSERT OR IGNORE INTO oauth_brokers "
                "(id, type, client_id, client_secret_enc, project_id, environment, default_external_user_id) "
                "VALUES (?, 'pipedream', 'cid', ?, 'proj_test', 'development', ?)",
                (BROKER_ID, vault.encrypt("csec"), EXTERNAL_USER),
            )
            await db.execute(
                "INSERT OR IGNORE INTO apis (id, name, base_url, spec_path) VALUES (?, ?, ?, ?)",
                (JIRA_API_ID, "Jira Cloud", JIRA_BASE_URL, jira_path),
            )
            # Connect-label written by the connect-callback at connect time, carrying
            # the tenant binding the user supplied on the connect-link request.
            await db.execute(
                "INSERT OR REPLACE INTO oauth_broker_connect_labels "
                "(id, broker_id, external_user_id, app_slug, label, api_id, server_variables, created_at) "
                "VALUES (?, ?, ?, 'jira', 'acme jira', ?, ?, ?)",
                (
                    "lbl-jira",
                    BROKER_ID,
                    EXTERNAL_USER,
                    JIRA_API_ID,
                    json.dumps({"your-domain": "acme"}),
                    1.0,
                ),
            )
            await db.commit()

    asyncio.run(setup())

    # Mock the external Pipedream surface so discover_accounts runs offline.
    async def fake_token(self):
        return "fake-pd-token"

    async def fake_import(api_id):
        # API row is already seeded; nothing to fetch from the catalog.
        return None

    fake_accounts = {
        "accounts": [
            {"id": ACCOUNT_ID, "app": {"name_slug": "jira", "slug": "jira"}},
        ]
    }

    class _FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return fake_accounts

    class _FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **kw):
            return _FakeResp()

    monkeypatch.setattr(PipedreamOAuthBroker, "_get_access_token", fake_token)
    monkeypatch.setattr("src.brokers.pipedream.ensure_catalog_api_imported", fake_import)
    monkeypatch.setattr("src.brokers.pipedream.httpx.AsyncClient", _FakeClient)

    yield

    async def teardown():
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "DELETE FROM credential_routes WHERE credential_id IN "
                "(SELECT id FROM credentials WHERE id LIKE ?)",
                (f"{BROKER_ID}-{ACCOUNT_ID}-%",),
            )
            await db.execute(
                "DELETE FROM credentials WHERE id LIKE ?", (f"{BROKER_ID}-{ACCOUNT_ID}-%",)
            )
            await db.execute("DELETE FROM oauth_broker_accounts WHERE broker_id=?", (BROKER_ID,))
            await db.execute(
                "DELETE FROM oauth_broker_connect_labels WHERE broker_id=?", (BROKER_ID,)
            )
            await db.execute("DELETE FROM oauth_brokers WHERE id=?", (BROKER_ID,))
            await db.execute("DELETE FROM apis WHERE id=?", (JIRA_API_ID,))
            await db.commit()

    asyncio.run(teardown())


def test_pipedream_jira_credential_carries_tenant(jira_pipedream_env):
    """discover_accounts must resolve the tenant host and persist server_variables.

    Regression for #485 on the Pipedream path: before the fix the credential was
    created with no server_variables and a route to the tenant-less / templated
    host, so the broker could never reach acme.atlassian.net.
    """

    async def run():
        broker = PipedreamOAuthBroker(
            broker_id=BROKER_ID,
            client_id="cid",
            client_secret="csec",
            project_id="proj_test",
            environment="development",
            default_external_user_id=EXTERNAL_USER,
        )
        count = await broker.discover_accounts(EXTERNAL_USER)
        assert count >= 1, "expected at least one discovered account-host pair"

        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT id, api_id, server_variables FROM credentials WHERE id LIKE ?",
                (f"{BROKER_ID}-{ACCOUNT_ID}-%",),
            ) as cur:
                cred = await cur.fetchone()
            assert cred is not None, "pipedream credential was not created"
            cred_id, api_id, sv_raw = cred

            # server_variables must be persisted so the broker can re-resolve.
            assert sv_raw, "credential is missing server_variables (tenant binding lost)"
            assert json.loads(sv_raw) == {"your-domain": "acme"}

            # The credential's route host must be the concrete tenant host.
            async with db.execute(
                "SELECT host FROM credential_routes WHERE credential_id=?", (cred_id,)
            ) as cur:
                routes = {r[0] for r in await cur.fetchall()}
            assert "acme.atlassian.net" in routes, f"expected tenant host route, got: {routes}"
            assert "{your-domain}.atlassian.net" not in routes, (
                f"templated host leaked into routes: {routes}"
            )

    asyncio.run(run())


def test_pipedream_credential_resolves_via_server_url(jira_pipedream_env):
    """The stored server_variables resolve to the tenant host through the vault helper.

    This mirrors the broker-time _resolve_routing_host path: given the credential's
    api_id + server_variables, vault._resolve_server_url must yield the tenant host.
    """

    async def run():
        broker = PipedreamOAuthBroker(
            broker_id=BROKER_ID,
            client_id="cid",
            client_secret="csec",
            project_id="proj_test",
            environment="development",
            default_external_user_id=EXTERNAL_USER,
        )
        await broker.discover_accounts(EXTERNAL_USER)

        resolved = await vault._resolve_server_url(JIRA_API_ID, {"your-domain": "acme"})
        assert resolved == "https://acme.atlassian.net", (
            f"expected tenant-resolved URL, got: {resolved}"
        )

    asyncio.run(run())
