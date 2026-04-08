"""Credential ambiguity tests — X-Jentic-Service header and ambiguity detection.

Tests the broker's behavior when multiple credentials resolve to the same
upstream host (e.g. Google Calendar + Gmail both on www.googleapis.com).
Uses direct DB setup to create the ambiguous state, then makes broker
requests to verify header behavior. The upstream calls will fail (non-routable)
but we can still verify the credential selection via response headers.
"""
import pytest


API_HOST = "127.0.0.2"
API_ID = API_HOST

CRED_ID_A = "test-cred-calendar"
CRED_ID_B = "test-cred-gmail"
APP_SLUG_A = "google_calendar"
APP_SLUG_B = "gmail"
BROKER_ID = "test-broker"


@pytest.fixture(scope="module")
def ambiguous_credentials(client, admin_session):
    """Set up two credentials for the same api_id with different app_slugs."""
    import aiosqlite
    import asyncio
    import os
    import src.vault as vault

    async def setup():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            # Register the API
            await db.execute(
                "INSERT OR IGNORE INTO apis (id, name, base_url) VALUES (?, ?, ?)",
                (API_ID, "Test API", f"https://{API_HOST}"),
            )

            # Create two encrypted credentials
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

            # Bind both to the default toolkit
            await db.execute(
                "INSERT OR IGNORE INTO toolkit_credentials (toolkit_id, credential_id) VALUES ('default', ?)",
                (CRED_ID_A,),
            )
            await db.execute(
                "INSERT OR IGNORE INTO toolkit_credentials (toolkit_id, credential_id) VALUES ('default', ?)",
                (CRED_ID_B,),
            )

            # Create oauth_broker_accounts entries with different app_slugs
            await db.execute(
                "INSERT OR IGNORE INTO oauth_brokers (id, type, client_id, client_secret_enc, project_id, environment, default_external_user_id, created_at) "
                "VALUES (?, 'pipedream', 'test', 'test', 'proj_test', 'development', 'default', 0)",
                (BROKER_ID,),
            )
            await db.execute(
                "INSERT OR IGNORE INTO oauth_broker_accounts "
                "(id, broker_id, external_user_id, api_host, app_slug, account_id, label, healthy, synced_at) "
                "VALUES (?, ?, 'default', ?, ?, 'apn_cal', 'Calendar', 1, 0)",
                (f"{BROKER_ID}:default:{API_HOST}:apn_cal", BROKER_ID, API_HOST, APP_SLUG_A),
            )
            await db.execute(
                "INSERT OR IGNORE INTO oauth_broker_accounts "
                "(id, broker_id, external_user_id, api_host, app_slug, account_id, label, healthy, synced_at) "
                "VALUES (?, ?, 'default', ?, ?, 'apn_gmail', 'Gmail', 1, 0)",
                (f"{BROKER_ID}:default:{API_HOST}:apn_gmail", BROKER_ID, API_HOST, APP_SLUG_B),
            )

            await db.commit()

    asyncio.run(setup())
    yield

    # Cleanup
    async def teardown():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            await db.execute("DELETE FROM toolkit_credentials WHERE credential_id IN (?, ?)", (CRED_ID_A, CRED_ID_B))
            await db.execute("DELETE FROM credentials WHERE id IN (?, ?)", (CRED_ID_A, CRED_ID_B))
            await db.execute("DELETE FROM oauth_broker_accounts WHERE broker_id=?", (BROKER_ID,))
            await db.execute("DELETE FROM oauth_brokers WHERE id=?", (BROKER_ID,))
            await db.execute("DELETE FROM apis WHERE id=?", (API_ID,))
            await db.commit()

    asyncio.run(teardown())


def test_ambiguous_credentials_set_header(client, agent_key_header, ambiguous_credentials):
    """When multiple credentials match and no service specified, X-Jentic-Credential-Ambiguous is set."""
    resp = client.get(f"/{API_HOST}/v1/test", headers=agent_key_header)
    # The upstream call will fail (non-routable) but we check response headers
    assert resp.headers.get("x-jentic-credential-ambiguous") == "true"
    assert resp.headers.get("x-jentic-credential-used") is not None


def test_service_header_selects_credential(client, agent_key_header, ambiguous_credentials):
    """X-Jentic-Service selects the right credential — no ambiguity header."""
    headers = {**agent_key_header, "X-Jentic-Service": APP_SLUG_A}
    resp = client.get(f"/{API_HOST}/v1/test", headers=headers)
    # Should not be ambiguous since we specified the service
    assert resp.headers.get("x-jentic-credential-ambiguous") is None


def test_unknown_service_falls_back(client, agent_key_header, ambiguous_credentials):
    """Unknown service name still makes the call (falls back to first credential)."""
    headers = {**agent_key_header, "X-Jentic-Service": "nonexistent_app"}
    resp = client.get(f"/{API_HOST}/v1/test", headers=headers)
    # Falls back — still ambiguous since the service didn't match
    assert resp.headers.get("x-jentic-credential-used") is not None


def test_alias_overrides_no_ambiguity(client, agent_key_header, ambiguous_credentials):
    """X-Jentic-Credential alias selects specific credential — no ambiguity."""
    headers = {**agent_key_header, "X-Jentic-Credential": CRED_ID_A}
    resp = client.get(f"/{API_HOST}/v1/test", headers=headers)
    assert resp.headers.get("x-jentic-credential-ambiguous") is None
    assert resp.headers.get("x-jentic-credential-used") == CRED_ID_A
