"""Unit tests for :generate-api-key endpoints (agents and service accounts)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from jentic_one.auth.services.agent_auth_service import AgentAuthService
from jentic_one.auth.services.errors import (
    ActorNotFoundError,
    AuthServiceError,
    InvalidTransitionError,
)
from jentic_one.auth.services.service_account_auth_service import ServiceAccountAuthService
from jentic_one.auth.web.deps import get_agent_auth_service, get_service_account_auth_service
from jentic_one.auth.web.errors import service_error_handler
from jentic_one.auth.web.routers import agents, service_accounts
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.web.deps import resolve_identity


def _admin_identity() -> Identity:
    return Identity(
        sub="usr_admin",
        email="admin@example.com",
        permissions=["agents:write", "service-accounts:write", "org:admin"],
    )


@pytest.fixture()
def mock_agent_auth_svc() -> MagicMock:
    return MagicMock(spec=AgentAuthService)


@pytest.fixture()
def mock_sa_auth_svc() -> MagicMock:
    return MagicMock(spec=ServiceAccountAuthService)


@pytest.fixture()
def client(mock_agent_auth_svc: MagicMock, mock_sa_auth_svc: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(agents.router)
    app.include_router(service_accounts.router)
    app.add_exception_handler(AuthServiceError, service_error_handler)
    app.dependency_overrides[resolve_identity] = _admin_identity
    app.dependency_overrides[get_agent_auth_service] = lambda: mock_agent_auth_svc
    app.dependency_overrides[get_service_account_auth_service] = lambda: mock_sa_auth_svc

    mock_ctx = MagicMock()
    app.state.ctx = mock_ctx
    return TestClient(app)


# ---------------------------------------------------------------------------
# Agent API key generation
# ---------------------------------------------------------------------------


def test_generate_agent_api_key_success(mock_agent_auth_svc: MagicMock, client: TestClient) -> None:
    mock_agent_auth_svc.register_api_key = AsyncMock(return_value="jak_test_plaintext_key")

    resp = client.post("/agents/agnt_active1:generate-api-key")

    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "jak_test_plaintext_key"


def test_generate_agent_api_key_not_found(
    mock_agent_auth_svc: MagicMock, client: TestClient
) -> None:
    mock_agent_auth_svc.register_api_key = AsyncMock(side_effect=ActorNotFoundError("agnt_missing"))

    resp = client.post("/agents/agnt_missing:generate-api-key")

    assert resp.status_code == 404


def test_generate_agent_api_key_not_active(
    mock_agent_auth_svc: MagicMock, client: TestClient
) -> None:
    mock_agent_auth_svc.register_api_key = AsyncMock(
        side_effect=InvalidTransitionError("agnt_pending", "pending", "generate-api-key")
    )

    resp = client.post("/agents/agnt_pending:generate-api-key")

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Service account API key generation
# ---------------------------------------------------------------------------


def test_generate_sa_api_key_success(mock_sa_auth_svc: MagicMock, client: TestClient) -> None:
    mock_sa_auth_svc.register_api_key = AsyncMock(return_value="jak_sa_test_key")

    resp = client.post("/service-accounts/sva_active1:generate-api-key")

    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "jak_sa_test_key"


def test_generate_sa_api_key_not_found(mock_sa_auth_svc: MagicMock, client: TestClient) -> None:
    mock_sa_auth_svc.register_api_key = AsyncMock(side_effect=ActorNotFoundError("sva_missing"))

    resp = client.post("/service-accounts/sva_missing:generate-api-key")

    assert resp.status_code == 404


def test_generate_sa_api_key_not_active(mock_sa_auth_svc: MagicMock, client: TestClient) -> None:
    mock_sa_auth_svc.register_api_key = AsyncMock(
        side_effect=InvalidTransitionError("sva_pending", "pending", "generate-api-key")
    )

    resp = client.post("/service-accounts/sva_pending:generate-api-key")

    assert resp.status_code == 409
