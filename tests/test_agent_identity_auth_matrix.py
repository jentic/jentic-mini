"""Auth boundary matrix for agent-identity routes (RFC 7591 / 7523 surfaces).

Each new admin and OAuth route is exercised under four principals:
  * anonymous    — no auth at all
  * tk_…         — legacy toolkit key
  * at_…         — minted agent access token
  * admin        — human session cookie

For every (route, principal) pair we assert the *category* of response —
401/403 for closed routes, 2xx/4xx for open routes — without binding to the
exact handler semantics. This catches regressions where a route quietly
becomes anonymous or where the human-only guard is dropped, without
turning into a brittle mock of the handler's error taxonomy.

The matrix is small by design: deeper happy/negative path coverage lives in
the route-specific test files (e.g. test_oauth_assertion_negative.py,
test_agents_admin_atomicity.py).
"""

from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from src.db import DB_PATH
from src.main import app
from tests.agent_identity_helpers import (
    make_assertion,
    make_ed25519_keypair,
    make_jwks,
    random_client_id,
)


_TEST_CLIENT_ADDR = ("127.0.0.1", 50000)
AUD = "http://testserver/oauth/token"


# ── Sync DB helpers ──────────────────────────────────────────────────────────
# Use sqlite3 (not aiosqlite) so fixtures can stay synchronous and avoid
# pytest-asyncio's async-fixture-injection-into-sync-test deprecation.


def _seed_approved_agent_sync(client_id: str, jwks: dict) -> None:
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """INSERT INTO agents (client_id, client_name, status, jwks_json, created_at)
               VALUES (?, ?, 'approved', ?, strftime('%s','now'))""",
            (client_id, f"matrix-{client_id}", json.dumps(jwks)),
        )
        db.commit()


def _cleanup_agent_sync(client_id: str) -> None:
    with sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM agent_tokens WHERE client_id=?", (client_id,))
        db.execute("DELETE FROM agent_nonces WHERE client_id=?", (client_id,))
        db.execute("DELETE FROM agents WHERE client_id=?", (client_id,))
        db.commit()


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def anon_tc(app):
    """A fresh, never-authenticated TestClient. Purposefully not session-scoped."""
    with TestClient(app, raise_server_exceptions=False, client=_TEST_CLIENT_ADDR) as c:
        yield c


@pytest.fixture
def tk_headers(agent_key):
    """Legacy toolkit-key auth header."""
    return {"X-Jentic-API-Key": agent_key}


@pytest.fixture
def admin_headers(admin_client):
    """Pull the cookie jar off the admin TestClient so we can present its
    session to a fresh client without sharing the underlying instance."""
    return {k: v for k, v in admin_client.cookies.items()}


@pytest.fixture
def at_token(client):  # noqa: ARG001 — depends on client to ensure migrations ran
    """Mint a real ``at_…`` against a freshly-seeded approved agent.

    Uses the live /oauth/token endpoint rather than poking the DB so the
    matrix exercises the actual mint path. The agent and tokens are torn
    down in the finaliser. Depends on ``client`` so the session-scoped
    lifespan (which runs migrations) has fired before we touch SQLite.
    """
    sk, x = make_ed25519_keypair()
    cid = random_client_id()
    _seed_approved_agent_sync(cid, make_jwks(x))

    with TestClient(app, raise_server_exceptions=False, client=_TEST_CLIENT_ADDR) as tc:
        r = tc.post(
            "/oauth/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": make_assertion(sk, iss=cid, aud=AUD),
            },
        )
        assert r.status_code == 200, r.text
        access_token = r.json()["access_token"]

    try:
        yield {"client_id": cid, "access_token": access_token}
    finally:
        _cleanup_agent_sync(cid)


@pytest.fixture
def at_token_pair(client):  # noqa: ARG001 — depends on client to ensure migrations ran
    """Yield a fresh (access_token, refresh_token, client_id) — own minting."""
    sk, x = make_ed25519_keypair()
    cid = random_client_id()
    _seed_approved_agent_sync(cid, make_jwks(x))
    with TestClient(app, raise_server_exceptions=False, client=_TEST_CLIENT_ADDR) as tc:
        r = tc.post(
            "/oauth/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": make_assertion(sk, iss=cid, aud=AUD),
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
    try:
        yield {
            "client_id": cid,
            "access_token": body["access_token"],
            "refresh_token": body["refresh_token"],
        }
    finally:
        _cleanup_agent_sync(cid)


# ── Matrix ────────────────────────────────────────────────────────────────────

# Category labels — what the matrix asserts the response *kind* is.
ALLOWED = "allowed"  # 2xx OR a 4xx that is not 401/403 (handler-level error)
UNAUTH = "unauth"  # exactly 401
FORBIDDEN = "forbidden"  # exactly 403


# Routes that admin operates with on agents. Path placeholders are bound to a
# guaranteed-missing client_id — the boundary check is independent of whether
# the row exists.
_ADMIN_AGENT_ROUTES: list[tuple[str, str]] = [
    ("GET", "/agents"),
    ("GET", "/agents/agnt_doesnotexist_xxxxxxxxxxx"),
    ("POST", "/agents/agnt_doesnotexist_xxxxxxxxxxx/approve"),
    ("POST", "/agents/agnt_doesnotexist_xxxxxxxxxxx/deny"),
    ("POST", "/agents/agnt_doesnotexist_xxxxxxxxxxx/disable"),
    ("POST", "/agents/agnt_doesnotexist_xxxxxxxxxxx/enable"),
    ("PUT", "/agents/agnt_doesnotexist_xxxxxxxxxxx/jwks"),
    ("DELETE", "/agents/agnt_doesnotexist_xxxxxxxxxxx"),
    ("GET", "/agents/agnt_doesnotexist_xxxxxxxxxxx/grants"),
    ("POST", "/agents/agnt_doesnotexist_xxxxxxxxxxx/grants"),
    ("PUT", "/agents/agnt_doesnotexist_xxxxxxxxxxx/grants"),
    ("DELETE", "/agents/agnt_doesnotexist_xxxxxxxxxxx/grants/default"),
]


def _classify(status: int) -> str:
    if status == 401:
        return UNAUTH
    if status == 403:
        return FORBIDDEN
    return ALLOWED


def _maybe_body(method: str) -> dict | None:
    return {} if method in ("POST", "PUT") else None


@pytest.mark.parametrize("method,path", _ADMIN_AGENT_ROUTES)
def test_admin_agent_routes_block_anonymous(anon_tc, method, path):
    """Anonymous callers must see 401 from every admin agent route."""
    status = anon_tc.request(method, path, json=_maybe_body(method)).status_code
    assert _classify(status) == UNAUTH, (
        f"{method} {path} returned {status} for anonymous — expected 401"
    )


@pytest.mark.parametrize("method,path", _ADMIN_AGENT_ROUTES)
def test_admin_agent_routes_block_toolkit_key(app, tk_headers, method, path):
    """Legacy ``tk_…`` keys must NOT reach admin agent routes — these are
    human-only. A 403 (or 401 from middleware) is acceptable; 2xx is not.
    """
    with TestClient(app, raise_server_exceptions=False, client=_TEST_CLIENT_ADDR) as tc:
        status = tc.request(method, path, headers=tk_headers, json=_maybe_body(method)).status_code
    assert _classify(status) in {UNAUTH, FORBIDDEN}, (
        f"{method} {path} returned {status} with a tk_ key — expected 401 or 403"
    )


@pytest.mark.parametrize("method,path", _ADMIN_AGENT_ROUTES)
def test_admin_agent_routes_block_agent_token(app, at_token, method, path):
    """Agent ``at_…`` tokens must NOT reach admin agent routes either."""
    headers = {"Authorization": f"Bearer {at_token['access_token']}"}
    with TestClient(app, raise_server_exceptions=False, client=_TEST_CLIENT_ADDR) as tc:
        status = tc.request(method, path, headers=headers, json=_maybe_body(method)).status_code
    assert _classify(status) in {UNAUTH, FORBIDDEN}, (
        f"{method} {path} returned {status} with an at_ token — expected 401 or 403"
    )


@pytest.mark.parametrize("method,path", _ADMIN_AGENT_ROUTES)
def test_admin_agent_routes_admin_session_passes_auth(app, admin_headers, method, path):
    """An authenticated admin must clear the auth boundary. Handler-level
    errors (404, 409, 422) are acceptable — we only assert auth admitted us.
    """
    with TestClient(app, raise_server_exceptions=False, client=_TEST_CLIENT_ADDR) as tc:
        for k, v in admin_headers.items():
            tc.cookies.set(k, v)
        status = tc.request(method, path, json=_maybe_body(method)).status_code
    assert _classify(status) == ALLOWED, (
        f"{method} {path} returned {status} for admin — expected 2xx or non-auth 4xx"
    )


# ── /oauth/revoke matrix ──────────────────────────────────────────────────────
#
# Revoke is *not* anonymous and is *not* admin-only — it only accepts an
# at_… or a human session, and the handler verifies that the caller can
# actually revoke the token they're presenting (same client_id, or admin).
# tk_… keys are deliberately excluded: revocation is RFC 7009-style and
# binds the credential to the token holder.


def test_revoke_anonymous_rejected(anon_tc):
    r = anon_tc.post("/oauth/revoke", data={"token": "rt_notreal"})
    assert r.status_code == 401


def test_revoke_toolkit_key_rejected(app, tk_headers):
    """tk_ keys are not the revocation principal per RFC 7009 — must 401/403."""
    with TestClient(app, raise_server_exceptions=False, client=_TEST_CLIENT_ADDR) as tc:
        r = tc.post("/oauth/revoke", headers=tk_headers, data={"token": "rt_notreal"})
    assert r.status_code in (401, 403)


def test_revoke_self_with_at_succeeds(app, at_token_pair):
    """Self-revocation by the holding agent — happy path."""
    headers = {"Authorization": f"Bearer {at_token_pair['access_token']}"}
    with TestClient(app, raise_server_exceptions=False, client=_TEST_CLIENT_ADDR) as tc:
        r = tc.post(
            "/oauth/revoke",
            headers=headers,
            data={"token": at_token_pair["refresh_token"]},
        )
    assert r.status_code == 200, r.text


def test_revoke_other_with_at_forbidden(app, at_token_pair):
    """Agent A's at_ must NOT be able to revoke agent B's token — same-client
    binding is what stops a leaked at_ from chain-revoking neighbours.
    """
    sk_b, x_b = make_ed25519_keypair()
    cid_b = random_client_id()
    _seed_approved_agent_sync(cid_b, make_jwks(x_b))
    try:
        with TestClient(app, raise_server_exceptions=False, client=_TEST_CLIENT_ADDR) as tc:
            r = tc.post(
                "/oauth/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": make_assertion(sk_b, iss=cid_b, aud=AUD),
                },
            )
            assert r.status_code == 200
            victim_rt = r.json()["refresh_token"]

            attacker_headers = {"Authorization": f"Bearer {at_token_pair['access_token']}"}
            r2 = tc.post(
                "/oauth/revoke",
                headers=attacker_headers,
                data={"token": victim_rt},
            )
            assert r2.status_code == 403, r2.text
    finally:
        _cleanup_agent_sync(cid_b)


# ── /register read endpoint matrix ────────────────────────────────────────────
#
# GET /register/{client_id} is the RFC 7592 client configuration endpoint —
# protected by the registration access token (rat_…), not by an admin
# session and not by tk_/at_. Anonymous reads must 401.


def test_register_read_anonymous_rejected(anon_tc):
    r = anon_tc.get("/register/agnt_does_not_exist_xxxxxxxxxx")
    assert r.status_code == 401


def test_register_read_with_random_bearer_rejected(anon_tc):
    r = anon_tc.get(
        "/register/agnt_does_not_exist_xxxxxxxxxx",
        headers={"Authorization": "Bearer rat_not_a_real_token"},
    )
    assert r.status_code in (401, 404)


# ── /oauth/token + /register publicness ───────────────────────────────────────


def test_oauth_token_endpoint_is_public(anon_tc):
    """The token endpoint authenticates *via* the assertion, not via prior
    auth — sending nothing yields a 4xx oauth error, not 401.
    """
    r = anon_tc.post("/oauth/token", data={"grant_type": "client_credentials"})
    assert r.status_code == 400
    assert r.json()["error"] == "unsupported_grant_type"


def test_register_endpoint_is_public(anon_tc):
    """RFC 7591 registration is open by design — anonymous POST creates a
    pending agent, even though the result is gated until human approval.
    """
    _, x = make_ed25519_keypair()
    r = anon_tc.post(
        "/register",
        json={"client_name": "matrix-public-register", "jwks": make_jwks(x)},
    )
    # Permissive on duplicate-name 409 from previous runs of the suite.
    assert r.status_code in (200, 201, 409), r.text
    if r.status_code in (200, 201):
        cid = r.json()["client_id"]
        _cleanup_agent_sync(cid)
