"""Unit tests for JWKS endpoint with populated keys."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from jentic_one.auth.web.routers import discovery
from jentic_one.shared.config import AuthConfig, SigningKeyConfig

TEST_KEY_PEM = (
    "-----BEGIN PRIVATE KEY-----\n"
    "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgg+NyrINDm09AtfDc\n"
    "E1rrXEDFFRHyQvFRTaGyLgOTHDShRANCAAQzqcdkuHnRKQqFTPhCK7Xeg8YE+3AO\n"
    "kaHwF9Pzjob5U+FdMegYHUc+K991gdxu2k1sdbXtG7dw5RHStrJveVDK\n"
    "-----END PRIVATE KEY-----\n"
)


@pytest.fixture()
def client_with_keys() -> TestClient:
    app = FastAPI()
    app.include_router(discovery.router)
    mock_ctx = MagicMock()
    mock_ctx.config.auth = AuthConfig(
        canonical_base_url="https://auth.example.com",
        id_signing=[
            SigningKeyConfig(kid="key-1", private_key_pem=SecretStr(TEST_KEY_PEM)),
        ],
    )
    app.state.ctx = mock_ctx
    return TestClient(app)


@pytest.fixture()
def client_no_keys() -> TestClient:
    app = FastAPI()
    app.include_router(discovery.router)
    mock_ctx = MagicMock()
    mock_ctx.config.auth = AuthConfig(canonical_base_url="https://auth.example.com")
    app.state.ctx = mock_ctx
    return TestClient(app)


def test_jwks_returns_configured_key(client_with_keys: TestClient) -> None:
    resp = client_with_keys.get("/.well-known/jwks.json")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["keys"]) == 1
    assert data["keys"][0]["kid"] == "key-1"
    assert data["keys"][0]["alg"] == "ES256"
    assert data["keys"][0]["kty"] == "EC"
    assert data["keys"][0]["crv"] == "P-256"


def test_jwks_empty_when_no_keys(client_no_keys: TestClient) -> None:
    resp = client_no_keys.get("/.well-known/jwks.json")
    assert resp.status_code == 200
    assert resp.json() == {"keys": []}


def test_discovery_includes_authorization_endpoint(client_with_keys: TestClient) -> None:
    resp = client_with_keys.get("/.well-known/oauth-authorization-server")
    data = resp.json()
    assert data["authorization_endpoint"] == "https://auth.example.com/authorize"
    assert "authorization_code" in data["grant_types_supported"]
    assert "code" in data["response_types_supported"]
    assert "S256" in data["code_challenge_methods_supported"]
    assert "ES256" in data["id_token_signing_alg_values_supported"]
