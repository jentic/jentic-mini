"""Agent identity helpers: opaque token hashing, Ed25519 assertion JWT verification."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from src.config import AGENT_ASSERTION_MAX_AGE


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_client_id() -> str:
    return "agnt_" + secrets.token_urlsafe(18).replace("-", "")[:26]


def new_access_token() -> str:
    return "at_" + secrets.token_urlsafe(24).rstrip("=")


def new_refresh_token() -> str:
    return "rt_" + secrets.token_urlsafe(32).rstrip("=")


def new_registration_access_token() -> str:
    return "rat_" + secrets.token_urlsafe(32).rstrip("=")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def wiped_agent_jwks_json() -> str:
    """Stored on declined / deregistered agents so no Ed25519 key remains for auth."""
    return json.dumps({"keys": []})


# Keys we accept and persist on a JWK. Anything else is dropped before
# storage so an agent can't smuggle arbitrary attributes into the row, and so
# the GET /register/{client_id} reflection never echoes back fields we never
# vetted. Private-key params (d, p, q, dp, dq, qi) are rejected outright by
# _reject_private_key_material — never stripped, because their presence is a
# protocol error, not an unknown field.
_PUBLIC_JWK_FIELDS = frozenset({"kty", "crv", "x", "kid", "alg", "use"})
_PRIVATE_JWK_FIELDS = frozenset({"d", "p", "q", "dp", "dq", "qi"})

# Hard cap on the serialised JWKS payload accepted at registration. A single
# Ed25519 public-key JWK is well under 200 bytes; this cap is generous enough
# for forward compatibility without permitting an agent to plant a multi-MB
# "jwks" blob in the agents table.
JWKS_MAX_BYTES = 4096


def _reject_private_key_material(key: dict[str, Any]) -> None:
    for field in _PRIVATE_JWK_FIELDS:
        if field in key:
            raise ValueError("jwks must not contain private key material")


def sanitise_jwks(jwks: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalise a JWKS submitted at registration / key rotation.

    Accepts a single OKP / Ed25519 public-key JWK. Returns a JWKS with each
    key stripped to the whitelisted public fields — so unknown attributes are
    silently dropped rather than persisted and reflected back via
    GET /register/{client_id}. Raises ValueError on:

      * not exactly one key
      * wrong kty / crv
      * private-key parameters present
      * alg present but not "EdDSA"
      * use present but not "sig"
      * x missing, non-string, or empty
      * serialised length above JWKS_MAX_BYTES
    """
    keys = jwks.get("keys")
    if not isinstance(keys, list) or len(keys) != 1:
        raise ValueError("jwks must contain exactly one key")
    key = keys[0]
    if not isinstance(key, dict):
        raise ValueError("jwks key must be an object")
    _reject_private_key_material(key)
    if key.get("kty") != "OKP" or key.get("crv") != "Ed25519":
        raise ValueError("jwks key must be OKP / Ed25519")
    alg = key.get("alg")
    if alg is not None and alg != "EdDSA":
        raise ValueError("jwks key alg must be EdDSA when present")
    use = key.get("use")
    if use is not None and use != "sig":
        raise ValueError("jwks key use must be 'sig' when present")
    x = key.get("x")
    if not isinstance(x, str) or not x:
        raise ValueError("jwks key missing x")

    cleaned_key = {k: v for k, v in key.items() if k in _PUBLIC_JWK_FIELDS}
    cleaned = {"keys": [cleaned_key]}
    if len(json.dumps(cleaned)) > JWKS_MAX_BYTES:
        raise ValueError("jwks too large")
    return cleaned


def extract_jwks_public_key_x(jwks: dict[str, Any]) -> str:
    """Return base64url `x` for the single OKP Ed25519 public key in jwks.

    Re-runs the same shape and private-material checks as ``sanitise_jwks`` so
    that even if a row was persisted before the sanitiser existed, a
    private-key-tainted JWKS cannot be used to verify an assertion.
    """
    keys = jwks.get("keys")
    if not isinstance(keys, list) or len(keys) != 1:
        raise ValueError("jwks must contain exactly one key")
    key = keys[0]
    if not isinstance(key, dict):
        raise ValueError("jwks key must be an object")
    _reject_private_key_material(key)
    if key.get("kty") != "OKP" or key.get("crv") != "Ed25519":
        raise ValueError("jwks key must be OKP / Ed25519")
    x = key.get("x")
    if not isinstance(x, str) or not x:
        raise ValueError("jwks key missing x")
    return x


def verify_jwt_bearer_assertion(
    assertion: str,
    public_key_x_b64url: str,
    *,
    expected_iss: str,
    expected_aud: str,
    max_age_seconds: int = AGENT_ASSERTION_MAX_AGE,
) -> dict[str, Any]:
    """Verify RFC 7523 client assertion (EdDSA / Ed25519). Returns payload dict."""
    parts = assertion.split(".")
    if len(parts) != 3:
        raise ValueError("invalid_assertion_format")

    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    try:
        header = json.loads(_b64url_decode(parts[0]))
        payload = json.loads(_b64url_decode(parts[1]))
        sig = _b64url_decode(parts[2])
    except Exception as exc:
        raise ValueError("invalid_assertion_encoding") from exc

    alg = header.get("alg")
    # RFC 8037 §3.1: only "EdDSA" is a JWS alg value. "Ed25519" is the JWK crv,
    # not a signing algorithm, even though some libraries use it loosely.
    if alg != "EdDSA":
        raise ValueError("invalid_assertion_alg")

    try:
        raw_pub = _b64url_decode(public_key_x_b64url)
    except Exception as exc:
        raise ValueError("invalid_jwks_x") from exc
    if len(raw_pub) != 32:
        raise ValueError("invalid_ed25519_public_key_length")

    pub = Ed25519PublicKey.from_public_bytes(raw_pub)
    try:
        pub.verify(sig, signing_input)
    except InvalidSignature as exc:
        raise ValueError("invalid_assertion_signature") from exc

    now = time.time()
    iss = payload.get("iss")
    if iss != expected_iss:
        raise ValueError("invalid_assertion_iss")
    aud = payload.get("aud")
    if aud != expected_aud:
        raise ValueError("invalid_assertion_aud")

    exp = payload.get("exp")
    iat = payload.get("iat")
    if not isinstance(exp, (int, float)) or not isinstance(iat, (int, float)):
        raise ValueError("invalid_assertion_time_claims")
    if exp < now:
        raise ValueError("assertion_expired")
    if exp - iat > max_age_seconds + 60:
        raise ValueError("assertion_ttl_too_long")
    if iat > now + 120:
        raise ValueError("assertion_iat_future")
    if now - iat > max_age_seconds:
        raise ValueError("assertion_stale")

    jti = payload.get("jti")
    if not jti or not isinstance(jti, str):
        raise ValueError("invalid_assertion_jti")

    return payload
