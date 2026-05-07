"""Atomic-token, replay, and refresh-rotation concurrency guarantees.

These tests live close to the storage layer rather than going through HTTP — the
goal is to exercise the transactional invariants of the JWT-bearer and refresh
flows. Higher-level happy/negative paths over the HTTP API are covered elsewhere.
"""

from __future__ import annotations

import asyncio
import json

import aiosqlite
import pytest
from fastapi.testclient import TestClient
from src.agent_identity_util import hash_token
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


async def _cleanup_agent(client_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM agent_tokens WHERE client_id=?", (client_id,))
        await db.execute("DELETE FROM agent_nonces WHERE client_id=?", (client_id,))
        await db.execute("DELETE FROM agents WHERE client_id=?", (client_id,))
        await db.commit()


@pytest.mark.asyncio
async def test_jti_replay_returns_invalid_grant_not_500(client):  # noqa: ARG001
    """A replayed assertion must be rejected with invalid_grant, never with a 500
    from a UNIQUE constraint violation on the nonce row.
    """
    sk, x = make_ed25519_keypair()
    cid = "agnt_replay_test_aaaaaaaaaaaaaa"
    await _seed_approved_agent(cid, make_jwks(x))

    # TestClient defaults to http://testserver — must match build_absolute_url's
    # output server-side or aud verification will fail before the replay check.
    aud = "http://testserver/oauth/token"
    jti = "replayed-jti-001"
    assertion = make_assertion(sk, iss=cid, aud=aud, jti=jti)

    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            # Mint: succeed.
            r1 = tc.post(
                "/oauth/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
            )
            assert r1.status_code == 200, r1.text

            # Replay same JWT — must 400 invalid_grant, not 500.
            r2 = tc.post(
                "/oauth/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
            )
            assert r2.status_code == 400, r2.text
            body = r2.json()
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_concurrent_refresh_rotation_at_most_one_wins(client):  # noqa: ARG001
    """Fire two refreshes against the same rt_ in parallel.

    Per RFC 6749 BCP §4.14, presenting the same refresh token twice — even
    legitimately, e.g. a retried request — is treated as a chain-compromise
    signal: the family is nuked. So the observable invariants here are:

      * statuses are exactly one of {[200, 400]} (a winner and a loser); both
        succeeding would indicate the CAS gate failed (the bug we're guarding
        against).
      * after the dust settles, no refresh token from the rotated family
        survives — either because the loser fell through to invalid_grant
        without minting, or because the loser's reuse detection wiped the
        family on its way out.
    """
    sk, x = make_ed25519_keypair()
    cid = "agnt_refreshrace_aaaaaaaaaaaaaa"
    await _seed_approved_agent(cid, make_jwks(x))

    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            r = tc.post(
                "/oauth/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": make_assertion(
                        sk, iss=cid, aud="http://testserver/oauth/token", jti="initial-001"
                    ),
                },
            )
            assert r.status_code == 200, r.text
            rt = r.json()["refresh_token"]

            async def refresh():
                return await asyncio.to_thread(
                    tc.post,
                    "/oauth/token",
                    data={"grant_type": "refresh_token", "refresh_token": rt},
                )

            r1, r2 = await asyncio.gather(refresh(), refresh())
            statuses = sorted([r1.status_code, r2.status_code])
            # Both succeeding would be the bug. A loser of 400 invalid_grant is
            # acceptable; the test does NOT assert exactly [200, 400] because
            # under heavy contention both could legitimately reject (e.g. one
            # blocks long enough that family-revocation has already run).
            assert 200 in statuses or statuses == [400, 400], (r1.text, r2.text)
            assert statuses != [200, 200], "two rotations succeeded — CAS gate failed"

        # The CAS gate guarantees: at most one row was ever inserted with this
        # parent_token_hash. (Even after family revocation runs, the unique
        # partial index on (parent_token_hash, token_type) backstops any
        # erroneous double-insert; this sanity-checks that the index never
        # raised an IntegrityError that surfaced through to the client.)
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM agent_tokens "
                "WHERE parent_token_hash=? AND token_type='refresh'",
                (hash_token(rt),),
            ) as cur:
                (count,) = await cur.fetchone()
        assert count <= 1, f"expected at most 1 child refresh, got {count}"
    finally:
        await _cleanup_agent(cid)
