"""Negative-branch coverage for JWT-bearer assertions at POST /oauth/token.

The verify_jwt_bearer_assertion path has many fail-closed branches (alg, aud,
iss, jti, iat, exp, signature, JWKS shape). Before this suite they were all
unguarded by tests — a regression that quietly accepts ``alg: none`` or a
mismatched aud would not fail CI. Each test here exercises one branch.

All malformed-assertion paths must collapse to ``invalid_grant`` per the
"no enumeration oracle" design — distinguishable error strings are an
information leak, so we only assert on the OAuth error code, not the
description.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid

import aiosqlite
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from src.db import DB_PATH
from src.main import app
from tests.agent_identity_helpers import (
    b64url_encode,
    make_assertion,
    make_ed25519_keypair,
    make_jwks,
)


# Same aud the production code computes (TestClient host = testserver, default
# scheme = http). Keep this in sync with build_canonical_url's fallback.
AUD = "http://testserver/oauth/token"


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
        await db.execute("DELETE FROM agents WHERE client_id=?", (client_id,))
        await db.commit()


def _post_token(tc: TestClient, assertion: str) -> tuple[int, dict]:
    r = tc.post(
        "/oauth/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
    )
    return r.status_code, r.json()


def _new_cid() -> str:
    return "agnt_" + uuid.uuid4().hex[:26]


def _hs256_assertion(*, iss: str, aud: str, secret: bytes = b"shh") -> str:
    """Hand-rolled HS256 token to verify alg pinning rejects symmetric algs."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": iss,
        "aud": aud,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
        "jti": uuid.uuid4().hex,
    }
    h_b = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p_b = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h_b}.{p_b}".encode("ascii")
    sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
    return f"{h_b}.{p_b}.{b64url_encode(sig)}"


def _none_alg_assertion(*, iss: str, aud: str) -> str:
    """Hand-rolled alg=none token (RFC 7519 §6) — must always be rejected."""
    header = {"alg": "none", "typ": "JWT"}
    payload = {
        "iss": iss,
        "aud": aud,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
        "jti": uuid.uuid4().hex,
    }
    h_b = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p_b = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    return f"{h_b}.{p_b}."


@pytest.mark.asyncio
async def test_alg_none_rejected(client):  # noqa: ARG001
    sk, x = make_ed25519_keypair()
    cid = _new_cid()
    await _seed_approved_agent(cid, make_jwks(x))
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            assertion = _none_alg_assertion(iss=cid, aud=AUD)
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_alg_hs256_rejected(client):  # noqa: ARG001
    sk, x = make_ed25519_keypair()
    cid = _new_cid()
    await _seed_approved_agent(cid, make_jwks(x))
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            assertion = _hs256_assertion(iss=cid, aud=AUD)
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_alg_ed25519_string_rejected(client):  # noqa: ARG001
    """RFC 8037 mandates ``alg: EdDSA`` — the curve name ``Ed25519`` is not a
    valid JWS alg. Accepting it would silently relax the algorithm pin.
    """
    sk, x = make_ed25519_keypair()
    cid = _new_cid()
    await _seed_approved_agent(cid, make_jwks(x))
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            assertion = make_assertion(sk, iss=cid, aud=AUD, alg="Ed25519")
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_aud_mismatch_rejected(client):  # noqa: ARG001
    sk, x = make_ed25519_keypair()
    cid = _new_cid()
    await _seed_approved_agent(cid, make_jwks(x))
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            assertion = make_assertion(sk, iss=cid, aud="https://attacker/oauth/token")
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_aud_missing_rejected(client):  # noqa: ARG001
    sk, x = make_ed25519_keypair()
    cid = _new_cid()
    await _seed_approved_agent(cid, make_jwks(x))
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            # Build a payload with no aud claim at all.
            header = {"alg": "EdDSA", "typ": "JWT"}
            payload = {
                "iss": cid,
                "iat": int(time.time()),
                "exp": int(time.time()) + 60,
                "jti": uuid.uuid4().hex,
            }
            h_b = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
            p_b = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
            signing_input = f"{h_b}.{p_b}".encode("ascii")
            sig = sk.sign(signing_input)
            assertion = f"{h_b}.{p_b}.{b64url_encode(sig)}"
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_iss_unknown_rejected(client):  # noqa: ARG001
    """An unknown iss must collapse to the same generic invalid_grant as a
    bad signature — distinguishable errors here are an enumeration oracle.
    """
    sk, _ = make_ed25519_keypair()
    with TestClient(app, raise_server_exceptions=False) as tc:
        assertion = make_assertion(sk, iss="agnt_does_not_exist_xxxxxxxx", aud=AUD)
        status, body = _post_token(tc, assertion)
        assert status == 400
        assert body["error"] == "invalid_grant"


@pytest.mark.asyncio
async def test_iss_missing_rejected(client):  # noqa: ARG001
    sk, _ = make_ed25519_keypair()
    with TestClient(app, raise_server_exceptions=False) as tc:
        # Forge a payload with no iss.
        header = {"alg": "EdDSA", "typ": "JWT"}
        payload = {
            "aud": AUD,
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
            "jti": uuid.uuid4().hex,
        }
        h_b = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
        p_b = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
        sig = sk.sign(f"{h_b}.{p_b}".encode("ascii"))
        assertion = f"{h_b}.{p_b}.{b64url_encode(sig)}"
        status, body = _post_token(tc, assertion)
        assert status == 400
        assert body["error"] == "invalid_grant"


@pytest.mark.asyncio
async def test_pending_agent_rejected_uniformly(client):  # noqa: ARG001
    """Status='pending' must be indistinguishable from unknown iss on the wire."""
    sk, x = make_ed25519_keypair()
    cid = _new_cid()
    await _seed_pending_agent(cid, make_jwks(x))
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            assertion = make_assertion(sk, iss=cid, aud=AUD)
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_expired_assertion_rejected(client):  # noqa: ARG001
    sk, x = make_ed25519_keypair()
    cid = _new_cid()
    await _seed_approved_agent(cid, make_jwks(x))
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            past = time.time() - 3600
            assertion = make_assertion(sk, iss=cid, aud=AUD, iat=past, exp=past + 60)
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_iat_too_old_rejected(client):  # noqa: ARG001
    """iat older than AGENT_ASSERTION_MAX_AGE must be rejected even if exp is
    in the future — bounds the replay window independently of exp.
    """
    sk, x = make_ed25519_keypair()
    cid = _new_cid()
    await _seed_approved_agent(cid, make_jwks(x))
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            far_past = time.time() - 24 * 3600
            assertion = make_assertion(sk, iss=cid, aud=AUD, iat=far_past, exp=time.time() + 3600)
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_iat_in_future_rejected(client):  # noqa: ARG001
    sk, x = make_ed25519_keypair()
    cid = _new_cid()
    await _seed_approved_agent(cid, make_jwks(x))
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            future = time.time() + 24 * 3600
            assertion = make_assertion(sk, iss=cid, aud=AUD, iat=future, exp=future + 60)
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_bad_signature_rejected(client):  # noqa: ARG001
    """Sign with one keypair, register the other — the signature must fail
    verification against the registered JWKS.
    """
    sk_signing, _ = make_ed25519_keypair()
    _, x_registered = make_ed25519_keypair()
    cid = _new_cid()
    await _seed_approved_agent(cid, make_jwks(x_registered))
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            assertion = make_assertion(sk_signing, iss=cid, aud=AUD)
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_malformed_jwt_returns_invalid_grant(client):  # noqa: ARG001
    """Two-part garbage must not 500."""
    with TestClient(app, raise_server_exceptions=False) as tc:
        status, body = _post_token(tc, "not-a-jwt")
        assert status == 400
        assert body["error"] == "invalid_grant"


@pytest.mark.asyncio
async def test_malformed_jwks_x_rejected(client):  # noqa: ARG001
    """Wrong-length / non-base64 ``x`` in the registered JWKS must be detected
    server-side. We seed an agent with junk ``x`` — even a valid signature
    will fail because the public key can't be reconstructed.
    """
    sk, _ = make_ed25519_keypair()
    cid = _new_cid()
    bad_jwks = {"keys": [{"kty": "OKP", "crv": "Ed25519", "x": "not_base64_!!!"}]}
    await _seed_approved_agent(cid, bad_jwks)
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            assertion = make_assertion(sk, iss=cid, aud=AUD)
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_multi_key_jwks_rejected(client):  # noqa: ARG001
    """``extract_jwks_public_key_x`` requires exactly one key in the JWKS — a
    multi-key payload fails closed regardless of which key signed. This keeps
    the verification path single-purpose; if multi-key support is ever added,
    update this test to assert kid-based selection instead.
    """
    sk_first, x_first = make_ed25519_keypair()
    _, x_second = make_ed25519_keypair()
    cid = _new_cid()
    multi = {
        "keys": [
            {"kty": "OKP", "crv": "Ed25519", "x": x_first, "kid": "k1"},
            {"kty": "OKP", "crv": "Ed25519", "x": x_second, "kid": "k2"},
        ]
    }
    await _seed_approved_agent(cid, multi)
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            assertion = make_assertion(sk_first, iss=cid, aud=AUD)
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_happy_path_mints_token_pair(client):  # noqa: ARG001
    """Counterpart to all the negative branches above — a well-formed
    assertion against a sane single-key JWKS yields ``(at_…, rt_…)``."""
    sk, x = make_ed25519_keypair()
    cid = _new_cid()
    await _seed_approved_agent(cid, make_jwks(x))
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            status, body = _post_token(tc, make_assertion(sk, iss=cid, aud=AUD))
            assert status == 200, body
            assert body["access_token"].startswith("at_")
            assert body["refresh_token"].startswith("rt_")
            assert body["token_type"].lower() == "bearer"
            assert body["expires_in"] > 0
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_initial_mint_links_access_token_into_refresh_family(client):  # noqa: ARG001
    """The initial JWT-bearer grant must put both tokens into the same
    revocation family. Otherwise a refresh-reuse family wipe leaves the
    original access token alive — an unintended survival of a compromised
    chain. We assert that the access-token row's ``parent_token_hash``
    points at the refresh-token row's hash.
    """
    from src.agent_identity_util import hash_token  # noqa: PLC0415

    sk, x = make_ed25519_keypair()
    cid = _new_cid()
    await _seed_approved_agent(cid, make_jwks(x))
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            status, body = _post_token(tc, make_assertion(sk, iss=cid, aud=AUD))
            assert status == 200, body
            at_h = hash_token(body["access_token"])
            rt_h = hash_token(body["refresh_token"])

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT token_type, parent_token_hash FROM agent_tokens
                   WHERE token_hash IN (?, ?)""",
                (at_h, rt_h),
            ) as cur:
                rows = {r["token_type"]: r["parent_token_hash"] async for r in cur}

        assert rows["refresh"] is None, "refresh token is the family root"
        assert rows["access"] == rt_h, (
            "initial access token must point at its sibling refresh token "
            "so a family-revocation walk reaches it"
        )
    finally:
        await _cleanup_agent(cid)


@pytest.mark.asyncio
async def test_kty_not_okp_rejected(client):  # noqa: ARG001
    """A non-OKP JWKS (e.g. RSA) must be rejected — even before signature
    verification — because the server only supports Ed25519 / OKP.
    """
    sk, _ = make_ed25519_keypair()
    cid = _new_cid()
    rsa_like = {"keys": [{"kty": "RSA", "n": "AAAA", "e": "AQAB"}]}
    await _seed_approved_agent(cid, rsa_like)
    try:
        with TestClient(app, raise_server_exceptions=False) as tc:
            assertion = make_assertion(sk, iss=cid, aud=AUD)
            status, body = _post_token(tc, assertion)
            assert status == 400
            assert body["error"] == "invalid_grant"
    finally:
        await _cleanup_agent(cid)


def test_missing_assertion_returns_invalid_request(client):  # noqa: ARG001
    """Form-level validation: no assertion => invalid_request, not invalid_grant."""
    with TestClient(app, raise_server_exceptions=False) as tc:
        r = tc.post(
            "/oauth/token",
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer"},
        )
        assert r.status_code == 400
        assert r.json()["error"] == "invalid_request"


def test_unknown_grant_type_rejected(client):  # noqa: ARG001
    with TestClient(app, raise_server_exceptions=False) as tc:
        r = tc.post("/oauth/token", data={"grant_type": "client_credentials"})
        assert r.status_code == 400
        assert r.json()["error"] == "unsupported_grant_type"


def _ensure_signing_works():
    """Sanity import to fail fast if the helper API drifts (avoids a confusing
    KeyError in the suite above)."""
    sk = Ed25519PrivateKey.generate()
    assert sk.sign(b"x")
    base64.urlsafe_b64encode(b"x")  # regression guard for the b64 import


_ensure_signing_works()
