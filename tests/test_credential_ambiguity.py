"""Credential ambiguity tests — X-Jentic-Service header and ambiguity detection.

Tests the broker's behavior when multiple credentials resolve to the same
upstream host (e.g. Google Calendar + Gmail both on www.googleapis.com).
Uses direct DB setup to create the ambiguous state, then makes broker
requests to verify header behavior. The upstream calls will fail (non-routable)
but we can still verify the credential selection via response headers.
"""

import asyncio
import os
import uuid

import aiosqlite
import pytest
import src.vault as vault


API_HOST = "127.0.0.2"
API_ID = API_HOST
HOST_SLUG = API_HOST.replace(".", "-")

ACCOUNT_ID_A = "apn_cal"
ACCOUNT_ID_B = "apn_gmail"
APP_SLUG_A = "google_calendar"
APP_SLUG_B = "gmail"
BROKER_ID = "test-ambig-broker"

# Credential IDs must match the broker_credential_id() pattern
CRED_ID_A = f"{BROKER_ID}-{ACCOUNT_ID_A}-{HOST_SLUG}"
CRED_ID_B = f"{BROKER_ID}-{ACCOUNT_ID_B}-{HOST_SLUG}"


@pytest.fixture(scope="module")
def ambiguous_credentials(client, admin_session):
    """Set up two credentials for the same api_id with different app_slugs."""

    async def setup():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            # Register the API
            await db.execute(
                "INSERT OR IGNORE INTO apis (id, name, base_url) VALUES (?, ?, ?)",
                (API_ID, "Test API", f"https://{API_HOST}"),
            )

            # Create two encrypted credentials with IDs matching broker_credential_id() pattern
            enc_a = vault.encrypt("fake-token-calendar")
            enc_b = vault.encrypt("fake-token-gmail")

            await db.execute(
                "INSERT OR IGNORE INTO credentials (id, label, env_var, encrypted_value, api_id, auth_type) "
                "VALUES (?, ?, ?, ?, ?, 'bearer')",
                (CRED_ID_A, "Calendar Token", "CRED_A", enc_a, API_ID),
            )
            await db.execute(
                "INSERT OR IGNORE INTO credentials (id, label, env_var, encrypted_value, api_id, auth_type) "
                "VALUES (?, ?, ?, ?, ?, 'bearer')",
                (CRED_ID_B, "Gmail Token", "CRED_B", enc_b, API_ID),
            )

            # Register routes so broker resolves credentials via credential_routes
            await db.execute(
                "INSERT OR IGNORE INTO credential_routes (credential_id, host) VALUES (?, ?)",
                (CRED_ID_A, API_HOST),
            )
            await db.execute(
                "INSERT OR IGNORE INTO credential_routes (credential_id, host) VALUES (?, ?)",
                (CRED_ID_B, API_HOST),
            )

            # Bind both to the default toolkit
            for cred_id in (CRED_ID_A, CRED_ID_B):
                await db.execute(
                    "INSERT OR IGNORE INTO toolkit_credentials (id, toolkit_id, credential_id) VALUES (?, 'default', ?)",
                    (str(uuid.uuid4()), cred_id),
                )

            # Create broker and account entries with different app_slugs
            await db.execute(
                "INSERT OR IGNORE INTO oauth_brokers (id, type, client_id, client_secret_enc, project_id, environment, default_external_user_id, created_at) "
                "VALUES (?, 'pipedream', 'test', 'test', 'proj_test', 'development', 'default', 0)",
                (BROKER_ID,),
            )
            await db.execute(
                "INSERT OR IGNORE INTO oauth_broker_accounts "
                "(id, broker_id, external_user_id, api_host, app_slug, account_id, label, healthy, synced_at) "
                "VALUES (?, ?, 'default', ?, ?, ?, 'Calendar', 1, 0)",
                (
                    f"{BROKER_ID}:default:{API_HOST}:{ACCOUNT_ID_A}",
                    BROKER_ID,
                    API_HOST,
                    APP_SLUG_A,
                    ACCOUNT_ID_A,
                ),
            )
            await db.execute(
                "INSERT OR IGNORE INTO oauth_broker_accounts "
                "(id, broker_id, external_user_id, api_host, app_slug, account_id, label, healthy, synced_at) "
                "VALUES (?, ?, 'default', ?, ?, ?, 'Gmail', 1, 0)",
                (
                    f"{BROKER_ID}:default:{API_HOST}:{ACCOUNT_ID_B}",
                    BROKER_ID,
                    API_HOST,
                    APP_SLUG_B,
                    ACCOUNT_ID_B,
                ),
            )

            await db.commit()

    asyncio.run(setup())
    yield

    async def teardown():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "DELETE FROM credential_routes WHERE credential_id IN (?, ?)",
                (CRED_ID_A, CRED_ID_B),
            )
            await db.execute(
                "DELETE FROM toolkit_credentials WHERE credential_id IN (?, ?)",
                (CRED_ID_A, CRED_ID_B),
            )
            await db.execute("DELETE FROM credentials WHERE id IN (?, ?)", (CRED_ID_A, CRED_ID_B))
            await db.execute("DELETE FROM oauth_broker_accounts WHERE broker_id=?", (BROKER_ID,))
            await db.execute("DELETE FROM oauth_brokers WHERE id=?", (BROKER_ID,))
            await db.execute("DELETE FROM apis WHERE id=?", (API_ID,))
            await db.commit()

    asyncio.run(teardown())


def test_ambiguous_credentials_set_header(client, agent_key_header, ambiguous_credentials):
    """When multiple credentials match and no service specified, X-Jentic-Credential-Ambiguous is set."""
    resp = client.get(f"/{API_HOST}/v1/test", headers=agent_key_header)
    assert resp.headers.get("x-jentic-credential-ambiguous") == "true"
    assert resp.headers.get("x-jentic-credential-used") is not None


def test_service_header_selects_credential(client, agent_key_header, ambiguous_credentials):
    """X-Jentic-Service selects the right credential — no ambiguity header."""
    headers = {**agent_key_header, "X-Jentic-Service": APP_SLUG_A}
    resp = client.get(f"/{API_HOST}/v1/test", headers=headers)
    assert resp.headers.get("x-jentic-credential-ambiguous") is None
    # Verify the correct credential was selected
    assert resp.headers.get("x-jentic-credential-used") == CRED_ID_A


def test_unknown_service_returns_409(client, agent_key_header, ambiguous_credentials):
    """Unknown service name returns 409 with available services listed."""
    headers = {**agent_key_header, "X-Jentic-Service": "nonexistent_app"}
    resp = client.get(f"/{API_HOST}/v1/test", headers=headers)
    assert resp.status_code == 409
    data = resp.json()
    assert data["error"] == "SERVICE_NOT_FOUND"
    assert "nonexistent_app" in data["message"]
    assert APP_SLUG_A in data["message"]
    assert APP_SLUG_B in data["message"]


def test_alias_overrides_no_ambiguity(client, agent_key_header, ambiguous_credentials):
    """X-Jentic-Credential alias selects specific credential — no ambiguity."""
    headers = {**agent_key_header, "X-Jentic-Credential": CRED_ID_A}
    resp = client.get(f"/{API_HOST}/v1/test", headers=headers)
    assert resp.headers.get("x-jentic-credential-ambiguous") is None
    assert resp.headers.get("x-jentic-credential-used") == CRED_ID_A


def test_ambiguous_selection_is_independent_of_row_order(
    client, agent_key_header, ambiguous_credentials
):
    """X-Jentic-Credential-Used reports the lex-min ID and stays unchanged
    after the route rows are rewritten in reverse physical order.

    Regression for #192: without a stable tie-breaker, the credential ID
    list returned by get_credential_ids_for_route — and therefore the
    first ID, which X-Jentic-Credential-Used reports — flipped whenever
    SQLite row order changed (VACUUM, reindex, delete+insert).
    """
    expected = min(CRED_ID_A, CRED_ID_B)

    resp1 = client.get(f"/{API_HOST}/v1/test", headers=agent_key_header)
    assert resp1.headers.get("x-jentic-credential-used") == expected

    async def _reverse_route_order():
        async with aiosqlite.connect(os.environ["DB_PATH"]) as db:
            await db.execute(
                "DELETE FROM credential_routes WHERE credential_id IN (?, ?)",
                (CRED_ID_A, CRED_ID_B),
            )
            for cid in (CRED_ID_B, CRED_ID_A):
                await db.execute(
                    "INSERT INTO credential_routes (credential_id, host) VALUES (?, ?)",
                    (cid, API_HOST),
                )
            await db.commit()

    asyncio.run(_reverse_route_order())

    resp2 = client.get(f"/{API_HOST}/v1/test", headers=agent_key_header)
    assert resp2.headers.get("x-jentic-credential-used") == expected
