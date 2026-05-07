"""JWKS hardening: registration must reject malformed / private-key / oversize JWKS,
and the assertion verifier must reject Ed25519-as-alg (RFC 8037 only allows EdDSA).
"""

from __future__ import annotations

import json

import pytest
from src.agent_identity_util import (
    JWKS_MAX_BYTES,
    extract_jwks_public_key_x,
    sanitise_jwks,
    verify_jwt_bearer_assertion,
)
from tests.agent_identity_helpers import (
    make_assertion,
    make_ed25519_keypair,
    make_jwks,
)


# ---------------------------------------------------------------------------
# sanitise_jwks: registration-time validator
# ---------------------------------------------------------------------------


def test_sanitise_jwks_strips_unknown_fields():
    """Unknown JWK fields must not survive into the persisted JWKS."""
    _, x = make_ed25519_keypair()
    jwks = {
        "keys": [
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "x": x,
                "kid": "k1",
                "alg": "EdDSA",
                "use": "sig",
                # Unknown fields the server should drop.
                "ext": True,
                "key_ops": ["verify"],
                "extra": "should-be-stripped",
            }
        ]
    }
    cleaned = sanitise_jwks(jwks)
    persisted_key = cleaned["keys"][0]
    assert set(persisted_key.keys()) == {"kty", "crv", "x", "kid", "alg", "use"}
    assert "ext" not in persisted_key
    assert "extra" not in persisted_key


@pytest.mark.parametrize("private_field", ["d", "p", "q", "dp", "dq", "qi"])
def test_sanitise_jwks_rejects_private_key_material(private_field):
    """A submitted JWKS containing private-key params must be refused outright,
    not silently sanitised — presence of those fields is a protocol error.
    """
    _, x = make_ed25519_keypair()
    jwks = make_jwks(x)
    jwks["keys"][0][private_field] = "AAAA"
    with pytest.raises(ValueError, match="private key material"):
        sanitise_jwks(jwks)


def test_sanitise_jwks_rejects_multi_key():
    _, x1 = make_ed25519_keypair()
    _, x2 = make_ed25519_keypair()
    jwks = {
        "keys": [
            {"kty": "OKP", "crv": "Ed25519", "x": x1},
            {"kty": "OKP", "crv": "Ed25519", "x": x2},
        ]
    }
    with pytest.raises(ValueError, match="exactly one key"):
        sanitise_jwks(jwks)


def test_sanitise_jwks_rejects_empty_keys():
    with pytest.raises(ValueError, match="exactly one key"):
        sanitise_jwks({"keys": []})


def test_sanitise_jwks_rejects_wrong_kty():
    jwks = {"keys": [{"kty": "RSA", "crv": "Ed25519", "x": "abc"}]}
    with pytest.raises(ValueError, match="OKP / Ed25519"):
        sanitise_jwks(jwks)


def test_sanitise_jwks_rejects_wrong_curve():
    jwks = {"keys": [{"kty": "OKP", "crv": "X25519", "x": "abc"}]}
    with pytest.raises(ValueError, match="OKP / Ed25519"):
        sanitise_jwks(jwks)


def test_sanitise_jwks_rejects_bad_alg():
    """The JWK ``alg`` field is optional, but if present must be EdDSA."""
    _, x = make_ed25519_keypair()
    jwks = make_jwks(x)
    jwks["keys"][0]["alg"] = "RS256"
    with pytest.raises(ValueError, match="alg must be EdDSA"):
        sanitise_jwks(jwks)


def test_sanitise_jwks_rejects_bad_use():
    _, x = make_ed25519_keypair()
    jwks = make_jwks(x)
    jwks["keys"][0]["use"] = "enc"
    with pytest.raises(ValueError, match="use must be 'sig'"):
        sanitise_jwks(jwks)


def test_sanitise_jwks_rejects_missing_x():
    jwks = {"keys": [{"kty": "OKP", "crv": "Ed25519"}]}
    with pytest.raises(ValueError, match="missing x"):
        sanitise_jwks(jwks)


def test_sanitise_jwks_rejects_oversize():
    """A JWKS payload larger than ``JWKS_MAX_BYTES`` must be refused so an
    attacker can't plant a multi-MB blob in the agents table.
    """
    _, x = make_ed25519_keypair()
    jwks = make_jwks(x)
    # Pad with a kid that's too long. Whitelisted, so survives stripping and
    # contributes to the serialised length.
    jwks["keys"][0]["kid"] = "a" * (JWKS_MAX_BYTES + 1)
    with pytest.raises(ValueError, match="too large"):
        sanitise_jwks(jwks)


def test_sanitise_jwks_rejects_non_object_key():
    with pytest.raises(ValueError, match="key must be an object"):
        sanitise_jwks({"keys": ["not-an-object"]})


# ---------------------------------------------------------------------------
# extract_jwks_public_key_x: defence-in-depth on the verification path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("private_field", ["d", "p", "q", "dp", "dq", "qi"])
def test_extract_jwks_rejects_private_material_in_persisted_row(private_field):
    """Even if a row was persisted before sanitise_jwks landed, the verifier
    must refuse to use a JWKS that carries private-key material.
    """
    _, x = make_ed25519_keypair()
    jwks = make_jwks(x)
    jwks["keys"][0][private_field] = "AAAA"
    with pytest.raises(ValueError, match="private key material"):
        extract_jwks_public_key_x(jwks)


# ---------------------------------------------------------------------------
# verify_jwt_bearer_assertion: alg must be exactly "EdDSA" (RFC 8037 §3.1)
# ---------------------------------------------------------------------------


def test_verify_assertion_rejects_ed25519_as_alg():
    """``Ed25519`` is the JWK ``crv`` — never a JWS ``alg``. Some libraries
    issue assertions with ``alg: Ed25519``; we used to accept those, which
    weakened our alg pinning. We now reject them.
    """
    sk, x = make_ed25519_keypair()
    iss = "agnt_test"
    aud = "http://testserver/oauth/token"
    assertion = make_assertion(sk, iss=iss, aud=aud, alg="Ed25519")
    with pytest.raises(ValueError, match="invalid_assertion_alg"):
        verify_jwt_bearer_assertion(assertion, x, expected_aud=aud)


def test_verify_assertion_accepts_eddsa():
    """Sanity check: the canonical EdDSA alg still verifies after the tighten."""
    sk, x = make_ed25519_keypair()
    iss = "agnt_test"
    aud = "http://testserver/oauth/token"
    assertion = make_assertion(sk, iss=iss, aud=aud, alg="EdDSA")
    payload = verify_jwt_bearer_assertion(assertion, x, expected_aud=aud)
    assert payload["iss"] == iss
    assert payload["aud"] == aud


# ---------------------------------------------------------------------------
# End-to-end: POST /register strips unknown fields and rejects bad input
# ---------------------------------------------------------------------------


def test_register_strips_unknown_jwk_fields_in_response_and_storage(client):
    """Registration must not echo or persist non-whitelisted JWK fields."""
    _, x = make_ed25519_keypair()
    body = {
        "client_name": "test-agent-strip",
        "jwks": {
            "keys": [
                {
                    "kty": "OKP",
                    "crv": "Ed25519",
                    "x": x,
                    "alg": "EdDSA",
                    "rogue_field": "should-not-be-persisted",
                }
            ]
        },
    }
    r = client.post("/register", json=body)
    assert r.status_code == 201, r.text
    persisted_key = r.json()["jwks"]["keys"][0]
    assert "rogue_field" not in persisted_key
    assert set(persisted_key.keys()) <= {"kty", "crv", "x", "kid", "alg", "use"}


def test_register_rejects_private_key_material(client):
    _, x = make_ed25519_keypair()
    body = {
        "client_name": "test-agent-private",
        "jwks": {"keys": [{"kty": "OKP", "crv": "Ed25519", "x": x, "d": "AAAA"}]},
    }
    r = client.post("/register", json=body)
    assert r.status_code == 400
    assert "private key material" in r.json()["detail"]


def test_register_rejects_oversize_jwks(client):
    _, x = make_ed25519_keypair()
    big = {"keys": [{"kty": "OKP", "crv": "Ed25519", "x": x, "kid": "a" * (JWKS_MAX_BYTES + 1)}]}
    # Sanity: the raw payload is larger than the cap so a server that didn't
    # cap pre-cleaning could still trip the check post-cleaning.
    assert len(json.dumps(big)) > JWKS_MAX_BYTES
    r = client.post("/register", json={"client_name": "too-big", "jwks": big})
    assert r.status_code == 400
    assert "too large" in r.json()["detail"]
