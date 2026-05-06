"""Test helpers for agent identity (Ed25519 keypair, assertion JWT, JWKS)."""

from __future__ import annotations

import base64
import json
import secrets
import time
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def make_ed25519_keypair() -> tuple[Ed25519PrivateKey, str]:
    """Return (private_key, base64url-encoded raw public key bytes)."""
    sk = Ed25519PrivateKey.generate()
    pk_raw = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return sk, _b64url_encode(pk_raw)


def make_jwks(public_x_b64url: str) -> dict:
    """Return a single-key OKP/Ed25519 JWKS object as the server expects."""
    return {"keys": [{"kty": "OKP", "crv": "Ed25519", "x": public_x_b64url}]}


def make_assertion(
    sk: Ed25519PrivateKey,
    *,
    iss: str,
    aud: str,
    jti: str | None = None,
    iat: float | None = None,
    exp: float | None = None,
    alg: str = "EdDSA",
    extra_payload: dict | None = None,
) -> str:
    """Mint a signed RFC 7523 client-assertion JWT with sensible defaults."""
    now = time.time() if iat is None else iat
    header = {"alg": alg, "typ": "JWT"}
    payload = {
        "iss": iss,
        "aud": aud,
        "iat": int(now),
        "exp": int((exp if exp is not None else now + 60)),
        "jti": jti or secrets.token_urlsafe(12),
    }
    if extra_payload:
        payload.update(extra_payload)

    h_b = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p_b = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h_b}.{p_b}".encode("ascii")
    sig = sk.sign(signing_input)
    return f"{h_b}.{p_b}.{_b64url_encode(sig)}"


def random_client_id() -> str:
    """Test-only client_id with the same shape as the production minter."""
    return "agnt_" + uuid.uuid4().hex[:26]
