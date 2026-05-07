"""Regression: agent-identity URLs are pinned to ``JENTIC_PUBLIC_BASE_URL``.

When the operator has set ``JENTIC_PUBLIC_BASE_URL`` (the canonical public
base URL of this Jentic Mini instance), the agent-identity routes must
derive the issuer / token aud / registration_client_uri from that
configuration rather than from the inbound ``Host:`` /
``X-Forwarded-Host:`` header. Otherwise an attacker who can spoof those
headers (directly to the container, or behind a permissive reverse proxy)
can:

  * have a captured assertion minted with a different aud accepted at the
    canonical token endpoint, by setting Host: to the canonical host, OR
  * poison the discovery document and the persisted
    ``registration_client_uri`` for legitimate registrations.
"""

from __future__ import annotations

import asyncio
import json
import time

import aiosqlite
import pytest
from fastapi.testclient import TestClient
from src.db import DB_PATH
from src.main import app
from tests.agent_identity_helpers import make_assertion, make_ed25519_keypair, make_jwks


PINNED = "https://jentic.canonical.example.com"


@pytest.fixture
def pinned_base_url(monkeypatch):
    """Pin JENTIC_PUBLIC_BASE_URL across both the config module and the
    utils module that imported its value (utils captures it at import time)."""
    monkeypatch.setattr("src.config.JENTIC_PUBLIC_BASE_URL", PINNED)
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_BASE_URL", PINNED)


def test_discovery_uses_pinned_base_url_regardless_of_host_header(pinned_base_url):
    """``GET /.well-known/oauth-authorization-server`` must advertise URLs on
    the pinned base, even when the request arrives with a different Host:.
    """
    with TestClient(app, raise_server_exceptions=False) as tc:
        r = tc.get(
            "/.well-known/oauth-authorization-server",
            headers={"Host": "attacker.example.com"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["issuer"] == PINNED
        assert body["token_endpoint"] == f"{PINNED}/oauth/token"
        assert body["registration_endpoint"] == f"{PINNED}/register"


def test_register_persists_canonical_client_uri(pinned_base_url):
    """``registration_client_uri`` must reflect the canonical base, not the
    Host: that the registering caller happens to have used.
    """
    _, x = make_ed25519_keypair()
    with TestClient(app, raise_server_exceptions=False) as tc:
        r = tc.post(
            "/register",
            json={"client_name": "pin-test", "jwks": make_jwks(x)},
            headers={"Host": "attacker.example.com"},
        )
        assert r.status_code == 201, r.text
        client_id = r.json()["client_id"]
        assert r.json()["registration_client_uri"].startswith(PINNED + "/register/")

    # Cleanup.
    async def _cleanup():
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM agents WHERE client_id=?", (client_id,))
            await db.commit()

    asyncio.run(_cleanup())


@pytest.mark.asyncio
async def test_assertion_minted_with_attacker_aud_rejected_against_canonical(
    pinned_base_url,
):
    """An assertion minted with ``aud = http://attacker/oauth/token`` must
    NOT verify when replayed against the canonical token endpoint, even if
    the attacker spoofs ``Host: attacker``. With the host-derived aud bug,
    the server would have recomputed the expected aud from the spoofed
    Host: and the signature would have verified.
    """
    sk, x = make_ed25519_keypair()
    cid = "agnt_pinned_aud_aaaaaaaaaaaaa"

    # Seed an approved agent so we get past the existence / status checks
    # and reach the aud verification.
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO agents (client_id, client_name, status, jwks_json, created_at)
               VALUES (?, ?, 'approved', ?, ?)""",
            (cid, f"test-{cid}", _jwks_to_json(make_jwks(x)), time.time()),
        )
        await db.commit()

    try:
        # The attacker mints with a non-canonical aud.
        attacker_aud = "http://attacker.example.com/oauth/token"
        assertion = make_assertion(sk, iss=cid, aud=attacker_aud)

        with TestClient(app, raise_server_exceptions=False) as tc:
            # Replay against the canonical endpoint, spoofing Host: to match
            # the attacker's aud. With the bug, the server would compute
            # expected_aud=http://attacker.example.com/oauth/token from the
            # spoofed header and the signature would verify.
            r = tc.post(
                "/oauth/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
                headers={"Host": "attacker.example.com"},
            )
            assert r.status_code == 400, r.text
            # The error code is the unified "invalid_grant" — the security
            # property is "did not mint", not "returned a particular string".
            assert r.json().get("error") == "invalid_grant"
    finally:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM agent_tokens WHERE client_id=?", (cid,))
            await db.execute("DELETE FROM agent_nonces WHERE client_id=?", (cid,))
            await db.execute("DELETE FROM agents WHERE client_id=?", (cid,))
            await db.commit()


def _jwks_to_json(jwks: dict) -> str:
    return json.dumps(jwks)
