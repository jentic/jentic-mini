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


def extract_jwks_public_key_x(jwks: dict[str, Any]) -> str:
    """Return base64url `x` for the single OKP Ed25519 public key in jwks."""
    keys = jwks.get("keys")
    if not isinstance(keys, list) or len(keys) != 1:
        raise ValueError("jwks must contain exactly one key")
    key = keys[0]
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
    if alg not in ("EdDSA", "Ed25519"):
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
