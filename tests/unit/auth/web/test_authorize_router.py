"""Unit tests for the authorize router helpers (state signing, redirect validation)."""

from __future__ import annotations

import time

import pytest

from jentic_one.auth.services.errors import InvalidGrantError
from jentic_one.auth.web.routers.authorize import (
    STATE_MAX_AGE_SECONDS,
    _is_allowed_redirect_uri,
    _sign_state,
    _verify_state,
)

SECRET = "test-secret-key"


def test_sign_verify_roundtrip() -> None:
    payload: dict[str, str | None] = {
        "client_id": "c1",
        "redirect_uri": "https://app.example.com/cb",
    }
    signed = _sign_state(payload, SECRET)
    result = _verify_state(signed, SECRET)
    assert result["client_id"] == "c1"
    assert result["redirect_uri"] == "https://app.example.com/cb"


def test_signature_length_is_128_bits() -> None:
    payload: dict[str, str | None] = {"key": "value"}
    signed = _sign_state(payload, SECRET)
    sig = signed.rsplit(".", 1)[1]
    assert len(sig) == 32


def test_invalid_signature_rejected() -> None:
    payload: dict[str, str | None] = {"key": "value"}
    signed = _sign_state(payload, SECRET)
    tampered = signed[:-1] + ("a" if signed[-1] != "a" else "b")
    with pytest.raises(InvalidGrantError, match="state signature invalid"):
        _verify_state(tampered, SECRET)


def test_wrong_secret_rejected() -> None:
    payload: dict[str, str | None] = {"key": "value"}
    signed = _sign_state(payload, SECRET)
    with pytest.raises(InvalidGrantError, match="state signature invalid"):
        _verify_state(signed, "wrong-secret")


def test_malformed_state_no_dot() -> None:
    with pytest.raises(InvalidGrantError, match="invalid state"):
        _verify_state("no-dot-here", SECRET)


def test_expired_state_rejected() -> None:
    payload: dict[str, str | None] = {
        "key": "value",
        "iat": str(int(time.time()) - STATE_MAX_AGE_SECONDS - 1),
    }
    signed = _sign_state(payload, SECRET)
    with pytest.raises(InvalidGrantError, match="state expired"):
        _verify_state(signed, SECRET)


def test_future_state_rejected() -> None:
    payload: dict[str, str | None] = {"key": "value", "iat": str(int(time.time()) + 100)}
    signed = _sign_state(payload, SECRET)
    with pytest.raises(InvalidGrantError, match="state expired"):
        _verify_state(signed, SECRET)


def test_state_within_ttl_accepted() -> None:
    payload: dict[str, str | None] = {"key": "value", "iat": str(int(time.time()) - 60)}
    signed = _sign_state(payload, SECRET)
    result = _verify_state(signed, SECRET)
    assert result["key"] == "value"


def test_state_without_iat_accepted() -> None:
    payload: dict[str, str | None] = {"key": "value"}
    signed = _sign_state(payload, SECRET)
    result = _verify_state(signed, SECRET)
    assert result["key"] == "value"


def test_redirect_same_origin_allowed() -> None:
    assert _is_allowed_redirect_uri("https://app.example.com/callback", "https://app.example.com")


def test_redirect_same_origin_with_path_allowed() -> None:
    assert _is_allowed_redirect_uri(
        "https://app.example.com/auth/callback", "https://app.example.com/"
    )


def test_redirect_different_host_rejected() -> None:
    assert not _is_allowed_redirect_uri("https://evil.com/callback", "https://app.example.com")


def test_redirect_different_scheme_rejected() -> None:
    assert not _is_allowed_redirect_uri(
        "http://app.example.com/callback", "https://app.example.com"
    )


def test_redirect_no_canonical_url_rejects_all() -> None:
    assert not _is_allowed_redirect_uri("https://app.example.com/callback", "")


def test_redirect_relative_uri_rejected() -> None:
    assert not _is_allowed_redirect_uri("/callback", "https://app.example.com")


def test_redirect_different_port_rejected() -> None:
    assert not _is_allowed_redirect_uri(
        "https://app.example.com:9999/callback", "https://app.example.com"
    )
