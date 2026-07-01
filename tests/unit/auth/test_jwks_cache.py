"""Unit tests for the shared JWKS caching module."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from jentic_one.shared.auth import CachedJWKSPublisher, resolve_agent_key
from jentic_one.shared.auth.jwks import _resolve_cached
from jentic_one.shared.config import AuthConfig, SigningKeyConfig

TEST_KEY_PEM = (
    "-----BEGIN PRIVATE KEY-----\n"
    "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgg+NyrINDm09AtfDc\n"
    "E1rrXEDFFRHyQvFRTaGyLgOTHDShRANCAAQzqcdkuHnRKQqFTPhCK7Xeg8YE+3AO\n"
    "kaHwF9Pzjob5U+FdMegYHUc+K991gdxu2k1sdbXtG7dw5RHStrJveVDK\n"
    "-----END PRIVATE KEY-----\n"
)

ED25519_JWKS = {
    "keys": [
        {
            "kty": "OKP",
            "crv": "Ed25519",
            "kid": "agent-key-1",
            "x": "11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo",
        }
    ]
}

ED25519_JWKS_MULTI = {
    "keys": [
        {
            "kty": "OKP",
            "crv": "Ed25519",
            "kid": "agent-key-1",
            "x": "11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo",
        },
        {
            "kty": "EC",
            "crv": "P-256",
            "kid": "wrong-type",
            "x": "abc",
            "y": "def",
        },
    ]
}


@pytest.fixture()
def auth_config() -> AuthConfig:
    return AuthConfig(
        canonical_base_url="https://auth.example.com",
        id_signing=[
            SigningKeyConfig(kid="key-1", private_key_pem=SecretStr(TEST_KEY_PEM)),
        ],
    )


@pytest.fixture(autouse=True)
def _clear_lru_cache() -> None:
    """Clear the LRU cache between tests."""
    _resolve_cached.cache_clear()


def test_publisher_returns_valid_jwks(auth_config: AuthConfig) -> None:
    publisher = CachedJWKSPublisher(auth_config)
    result = publisher.get_jwks()
    assert "keys" in result
    assert len(result["keys"]) == 1
    key = result["keys"][0]
    assert key["kid"] == "key-1"
    assert key["kty"] == "EC"
    assert key["crv"] == "P-256"
    assert key["alg"] == "ES256"


def test_publisher_repeated_calls_return_same_object(auth_config: AuthConfig) -> None:
    publisher = CachedJWKSPublisher(auth_config)
    first = publisher.get_jwks()
    second = publisher.get_jwks()
    assert first is second


def test_publisher_empty_config_returns_empty_keys() -> None:
    config = AuthConfig()
    publisher = CachedJWKSPublisher(config)
    assert publisher.get_jwks() == {"keys": []}


def test_publisher_multiple_keys() -> None:
    config = AuthConfig(
        id_signing=[
            SigningKeyConfig(kid="k1", private_key_pem=SecretStr(TEST_KEY_PEM)),
            SigningKeyConfig(kid="k2", private_key_pem=SecretStr(TEST_KEY_PEM)),
        ]
    )
    publisher = CachedJWKSPublisher(config)
    result = publisher.get_jwks()
    assert len(result["keys"]) == 2
    kids = {k["kid"] for k in result["keys"]}
    assert kids == {"k1", "k2"}


def test_resolve_agent_key_ed25519() -> None:
    key = resolve_agent_key(ED25519_JWKS)
    assert key is not None


def test_resolve_agent_key_by_kid() -> None:
    key = resolve_agent_key(ED25519_JWKS, kid="agent-key-1")
    assert key is not None


def test_resolve_agent_key_unknown_kid() -> None:
    key = resolve_agent_key(ED25519_JWKS, kid="nonexistent")
    assert key is None


def test_resolve_agent_key_skips_non_okp() -> None:
    key = resolve_agent_key(ED25519_JWKS_MULTI, kid="wrong-type")
    assert key is None


def test_resolve_agent_key_empty_jwks() -> None:
    key = resolve_agent_key({"keys": []})
    assert key is None


def test_resolve_agent_key_cache_hit() -> None:
    first = resolve_agent_key(ED25519_JWKS, kid="agent-key-1")
    second = resolve_agent_key(ED25519_JWKS, kid="agent-key-1")
    assert first is second
    assert _resolve_cached.cache_info().hits >= 1


def test_resolve_agent_key_invalid_data() -> None:
    bad_jwks = {"keys": [{"kty": "OKP", "crv": "Ed25519", "kid": "bad", "x": "!!!"}]}
    key = resolve_agent_key(bad_jwks, kid="bad")
    assert key is None
