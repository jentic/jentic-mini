"""Unit tests for service account scope management endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from jentic_one.auth.services.errors import AuthServiceError
from jentic_one.auth.services.service_account_service import ServiceAccountService
from jentic_one.auth.web.deps import get_service_account_service
from jentic_one.auth.web.errors import service_error_handler
from jentic_one.auth.web.routers import service_accounts
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.web.deps import resolve_identity


def _admin_identity() -> Identity:
    return Identity(
        sub="usr_admin",
        email="admin@example.com",
        permissions=["service-accounts:write", "service-accounts:read", "org:admin"],
    )


def _readonly_identity() -> Identity:
    return Identity(
        sub="usr_reader",
        email="reader@example.com",
        permissions=["service-accounts:read"],
    )


@pytest.fixture()
def mock_sa_svc() -> MagicMock:
    svc = MagicMock(spec=ServiceAccountService)
    svc.get_scopes = AsyncMock(return_value=["capabilities:execute", "agents:read"])
    svc.replace_scopes = AsyncMock(return_value=["new:scope"])
    return svc


@pytest.fixture()
def client(mock_sa_svc: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(service_accounts.router)
    app.add_exception_handler(AuthServiceError, service_error_handler)
    app.dependency_overrides[resolve_identity] = _admin_identity
    app.dependency_overrides[get_service_account_service] = lambda: mock_sa_svc

    mock_ctx = MagicMock()
    app.state.ctx = mock_ctx
    return TestClient(app)


@pytest.fixture()
def readonly_client(mock_sa_svc: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(service_accounts.router)
    app.add_exception_handler(AuthServiceError, service_error_handler)
    app.dependency_overrides[resolve_identity] = _readonly_identity
    app.dependency_overrides[get_service_account_service] = lambda: mock_sa_svc

    mock_ctx = MagicMock()
    app.state.ctx = mock_ctx
    return TestClient(app)


def test_get_scopes(client: TestClient) -> None:
    resp = client.get("/service-accounts/sa_test1/scopes")
    assert resp.status_code == 200
    assert resp.json() == {"scopes": ["capabilities:execute", "agents:read"]}


def test_get_scopes_requires_read(readonly_client: TestClient) -> None:
    resp = readonly_client.get("/service-accounts/sa_test1/scopes")
    assert resp.status_code == 200


def test_replace_scopes(client: TestClient) -> None:
    resp = client.put("/service-accounts/sa_test1/scopes", json={"scopes": ["new:scope"]})
    assert resp.status_code == 200
    assert resp.json() == {"scopes": ["new:scope"]}


def test_replace_scopes_empty(client: TestClient, mock_sa_svc: MagicMock) -> None:
    mock_sa_svc.replace_scopes = AsyncMock(return_value=[])
    resp = client.put("/service-accounts/sa_test1/scopes", json={"scopes": []})
    assert resp.status_code == 200
    assert resp.json() == {"scopes": []}


def test_replace_scopes_requires_write(readonly_client: TestClient) -> None:
    resp = readonly_client.put("/service-accounts/sa_test1/scopes", json={"scopes": ["x"]})
    assert resp.status_code == 403
