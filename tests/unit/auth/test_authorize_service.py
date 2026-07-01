"""Unit tests for the AuthorizeService PKCE verification logic."""

from __future__ import annotations

import hashlib
from base64 import urlsafe_b64encode

from jentic_one.auth.services.authorize_service import _hash_code, _verify_pkce


def test_pkce_valid_verifier_passes() -> None:
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = urlsafe_b64encode(digest).rstrip(b"=").decode()
    assert _verify_pkce(verifier, challenge) is True


def test_pkce_wrong_verifier_fails() -> None:
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = urlsafe_b64encode(digest).rstrip(b"=").decode()
    assert _verify_pkce("wrong-verifier", challenge) is False


def test_pkce_empty_verifier_fails() -> None:
    challenge = urlsafe_b64encode(hashlib.sha256(b"x").digest()).rstrip(b"=").decode()
    assert _verify_pkce("", challenge) is False


def test_hash_code_deterministic() -> None:
    assert _hash_code("test") == _hash_code("test")


def test_hash_code_different_inputs_differ() -> None:
    assert _hash_code("a") != _hash_code("b")


def test_hash_code_is_sha256_hex() -> None:
    result = _hash_code("test")
    assert len(result) == 64
    int(result, 16)
