"""Credential ambiguity tests — route-based resolution and disambiguation.

Tests the broker's behavior when multiple credentials have routes matching
the same upstream host. Uses direct DB setup, then makes broker requests
to verify header behavior. Upstream calls fail (non-routable) but we can
verify credential selection via response headers.
"""
import asyncio
import json
import os
import uuid

import aiosqlite
import pytest

import src.vault as vault


API_HOST = "127.0.0.2"
ROUTE_CALENDAR = f"{API_HOST}/calendar"
ROUTE_GMAIL = f"{API_HOST}/gmail"

CRED_ID_A = "work-calendar"
CRED_ID_B = "work-gmail"


@pytest.fixture(scope="module")
def ambiguous_credentials(client, admin_session):
    """Set up two credentials with different route prefixes for the same host."""

    async def setup():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            # Register the API (for scheme lookup)
            await db.execute(
                "INSERT OR IGNORE INTO apis (id, name, base_url) VALUES (?, ?, ?)",
                (API_HOST, "Test API", f"https://{API_HOST}"),
            )

            enc_a = vault.encrypt("fake-token-calendar")
            enc_b = vault.encrypt("fake-token-gmail")

            await db.execute(
                "INSERT OR IGNORE INTO credentials (id, label, env_var, encrypted_value, routes, auth_type) "
                "VALUES (?, ?, ?, ?, ?, 'bearer')",
                (CRED_ID_A, "Work Calendar", "CRED_A", enc_a, json.dumps([ROUTE_CALENDAR])),
            )
            await db.execute(
                "INSERT OR IGNORE INTO credentials (id, label, env_var, encrypted_value, routes, auth_type) "
                "VALUES (?, ?, ?, ?, ?, 'bearer')",
                (CRED_ID_B, "Work Gmail", "CRED_B", enc_b, json.dumps([ROUTE_GMAIL])),
            )

            for cred_id in (CRED_ID_A, CRED_ID_B):
                await db.execute(
                    "INSERT OR IGNORE INTO toolkit_credentials (id, toolkit_id, credential_id) VALUES (?, 'default', ?)",
                    (str(uuid.uuid4()), cred_id),
                )

            await db.commit()

    asyncio.run(setup())
    yield

    async def teardown():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            await db.execute("DELETE FROM toolkit_credentials WHERE credential_id IN (?, ?)", (CRED_ID_A, CRED_ID_B))
            await db.execute("DELETE FROM credentials WHERE id IN (?, ?)", (CRED_ID_A, CRED_ID_B))
            await db.execute("DELETE FROM apis WHERE id=?", (API_HOST,))
            await db.commit()

    asyncio.run(teardown())


def test_longest_prefix_selects_calendar(client, agent_key_header, ambiguous_credentials):
    """Request to /calendar/v3/events selects the calendar credential (longest prefix match)."""
    resp = client.get(f"/{API_HOST}/calendar/v3/events", headers=agent_key_header)
    assert resp.headers.get("x-jentic-credential-used") == CRED_ID_A
    # Not ambiguous — different prefix lengths
    assert resp.headers.get("x-jentic-credential-ambiguous") is None


def test_longest_prefix_selects_gmail(client, agent_key_header, ambiguous_credentials):
    """Request to /gmail/v1/messages selects the gmail credential."""
    resp = client.get(f"/{API_HOST}/gmail/v1/messages", headers=agent_key_header)
    assert resp.headers.get("x-jentic-credential-used") == CRED_ID_B
    assert resp.headers.get("x-jentic-credential-ambiguous") is None


def test_alias_overrides_route_match(client, agent_key_header, ambiguous_credentials):
    """X-Jentic-Credential overrides route matching."""
    headers = {**agent_key_header, "X-Jentic-Credential": CRED_ID_B}
    resp = client.get(f"/{API_HOST}/calendar/v3/events", headers=headers)
    # Alias forces gmail credential even for calendar path
    assert resp.headers.get("x-jentic-credential-used") == CRED_ID_B
    assert resp.headers.get("x-jentic-credential-ambiguous") is None
