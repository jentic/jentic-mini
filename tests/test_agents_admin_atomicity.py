"""Disable / deny / delete atomicity for agent identities.

These admin actions revoke an agent's access tokens, nonces, and grants in a
single transaction so a racing /oauth/token call cannot mint after the status
check has passed but before the cleanup commits. Disable also wipes
agent_nonces — without that, a re-enabled agent could replay an unexpired
``jti`` from before the disable.
"""

from __future__ import annotations

import json
import time

import aiosqlite
import pytest
from fastapi.testclient import TestClient
from src.agent_identity_util import hash_token
from src.config import AGENT_NONCE_WINDOW
from src.db import DB_PATH
from src.main import app
from tests.agent_identity_helpers import make_assertion, make_ed25519_keypair, make_jwks


async def _seed_approved_agent(client_id: str, jwks: dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO agents (client_id, client_name, status, jwks_json, created_at)
               VALUES (?, ?, 'approved', ?, strftime('%s','now'))""",
            (client_id, f"test-{client_id}", json.dumps(jwks)),
        )
        await db.commit()


async def _seed_pending_agent(client_id: str, jwks: dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO agents (client_id, client_name, status, jwks_json, created_at)
               VALUES (?, ?, 'pending', ?, strftime('%s','now'))""",
            (client_id, f"test-{client_id}", json.dumps(jwks)),
        )
        await db.commit()


async def _cleanup_agent(client_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM agent_tokens WHERE client_id=?", (client_id,))
        await db.execute("DELETE FROM agent_nonces WHERE client_id=?", (client_id,))
        await db.execute("DELETE FROM agent_toolkit_grants WHERE client_id=?", (client_id,))
        await db.execute("DELETE FROM agents WHERE client_id=?", (client_id,))
        await db.commit()


async def _count(query: str, params: tuple) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(query, params) as cur:
            return (await cur.fetchone())[0]


@pytest.mark.asyncio
async def test_disable_clears_tokens_and_nonces(admin_client):
    """POST /agents/{id}/disable must wipe tokens AND nonces in one transaction.

    Without the nonce wipe, an unexpired ``jti`` survives, and a subsequent
    re-enable would let an attacker replay the original assertion.
    """
    sk, x = make_ed25519_keypair()
    cid = "agnt_disable_atomic_aaaaaaaaaa"
    await _seed_approved_agent(cid, make_jwks(x))

    # Mint via the real endpoint so we exercise the same code path that lays
    # down both an access token row and a nonce row.
    aud = "http://testserver/oauth/token"
    assertion = make_assertion(sk, iss=cid, aud=aud)
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            r = tc.post(
                "/oauth/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
            )
            assert r.status_code == 200, r.text

        assert await _count("SELECT COUNT(*) FROM agent_tokens WHERE client_id=?", (cid,)) >= 1
        assert await _count("SELECT COUNT(*) FROM agent_nonces WHERE client_id=?", (cid,)) >= 1

        r = admin_client.post(f"/agents/{cid}/disable")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "disabled"

        # Both tables must be empty for this agent.
        assert await _count("SELECT COUNT(*) FROM agent_tokens WHERE client_id=?", (cid,)) == 0
        assert await _count("SELECT COUNT(*) FROM agent_nonces WHERE client_id=?", (cid,)) == 0
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_refresh_after_disable_is_rejected(admin_client):
    """A refresh token issued before disable must not mint a new pair."""
    sk, x = make_ed25519_keypair()
    cid = "agnt_disable_refresh_aaaaaaaaa"
    await _seed_approved_agent(cid, make_jwks(x))

    try:
        aud = "http://testserver/oauth/token"
        with TestClient(app, raise_server_exceptions=False) as tc:
            r = tc.post(
                "/oauth/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": make_assertion(sk, iss=cid, aud=aud),
                },
            )
            assert r.status_code == 200, r.text
            rt = r.json()["refresh_token"]

            # Disable through the admin route.
            assert admin_client.post(f"/agents/{cid}/disable").status_code == 200

            # The refresh token row was deleted by disable, so the refresh path
            # must return 400 invalid_grant — not 500, not 200.
            r2 = tc.post(
                "/oauth/token",
                data={"grant_type": "refresh_token", "refresh_token": rt},
            )
            assert r2.status_code == 400, r2.text
            assert r2.json()["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_deny_clears_nonces_and_grants(admin_client):
    """deny must wipe nonces AND grants AND any tokens the agent already had."""
    sk, x = make_ed25519_keypair()
    cid = "agnt_deny_atomic_aaaaaaaaaaaa"
    await _seed_pending_agent(cid, make_jwks(x))

    # Plant a token, a nonce, and a grant directly so we don't have to go through
    # approve-then-mint. The router must wipe all three regardless of how they
    # got there.
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO agent_tokens (token_hash, client_id, token_type, expires_at, created_at) "
            "VALUES (?, ?, 'access', ?, ?)",
            (hash_token("at_fake"), cid, now + 3600, now),
        )
        await db.execute(
            "INSERT INTO agent_nonces (jti, client_id, expires_at) VALUES (?, ?, ?)",
            ("jti-deny-test", cid, now + AGENT_NONCE_WINDOW),
        )
        # Plant a grant by inserting the toolkit row first if it doesn't exist.
        await db.execute(
            "INSERT OR IGNORE INTO toolkits (id, name, disabled) VALUES ('default', 'default', 0)"
        )
        await db.execute(
            "INSERT OR REPLACE INTO agent_toolkit_grants (client_id, toolkit_id, granted_at, granted_by) "
            "VALUES (?, 'default', ?, 'test')",
            (cid, now),
        )
        await db.commit()

    try:
        r = admin_client.post(f"/agents/{cid}/deny")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "denied"

        assert await _count("SELECT COUNT(*) FROM agent_tokens WHERE client_id=?", (cid,)) == 0
        assert await _count("SELECT COUNT(*) FROM agent_nonces WHERE client_id=?", (cid,)) == 0
        assert (
            await _count("SELECT COUNT(*) FROM agent_toolkit_grants WHERE client_id=?", (cid,)) == 0
        )
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_delete_clears_tokens_nonces_and_grants(admin_client):
    """DELETE /agents/{id} must soft-delete the agent and wipe associated rows."""
    sk, x = make_ed25519_keypair()
    cid = "agnt_delete_atomic_aaaaaaaaaa"
    await _seed_approved_agent(cid, make_jwks(x))

    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO agent_tokens (token_hash, client_id, token_type, expires_at, created_at) "
            "VALUES (?, ?, 'access', ?, ?)",
            (hash_token("at_delete_fake"), cid, now + 3600, now),
        )
        await db.execute(
            "INSERT INTO agent_nonces (jti, client_id, expires_at) VALUES (?, ?, ?)",
            ("jti-delete-test", cid, now + AGENT_NONCE_WINDOW),
        )
        await db.execute(
            "INSERT OR IGNORE INTO toolkits (id, name, disabled) VALUES ('default', 'default', 0)"
        )
        await db.execute(
            "INSERT OR REPLACE INTO agent_toolkit_grants (client_id, toolkit_id, granted_at, granted_by) "
            "VALUES (?, 'default', ?, 'test')",
            (cid, now),
        )
        await db.commit()

    try:
        r = admin_client.delete(f"/agents/{cid}")
        assert r.status_code == 204, r.text

        assert await _count("SELECT COUNT(*) FROM agent_tokens WHERE client_id=?", (cid,)) == 0
        assert await _count("SELECT COUNT(*) FROM agent_nonces WHERE client_id=?", (cid,)) == 0
        assert (
            await _count("SELECT COUNT(*) FROM agent_toolkit_grants WHERE client_id=?", (cid,)) == 0
        )
        # Soft-deleted: agents row still exists, deleted_at populated.
        assert (
            await _count(
                "SELECT COUNT(*) FROM agents WHERE client_id=? AND deleted_at IS NOT NULL",
                (cid,),
            )
            == 1
        )
    finally:
        await _cleanup_agent(cid)
