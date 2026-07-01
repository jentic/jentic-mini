"""Unit tests for the security-schemes endpoint."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jentic.problem_details import ProblemDetailException, problem_detail_exception_handler

from jentic_one.registry.services.errors import ApiNotFoundError, NoCurrentRevisionError
from jentic_one.registry.web.app import get_exception_handlers
from jentic_one.registry.web.routers import apis
from jentic_one.registry.web.schemas.apis import (
    SecuritySchemeFlowResponse,
    SecuritySchemeListResponse,
    SecuritySchemeResponse,
)
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.web.deps import resolve_identity


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ProblemDetailException, problem_detail_exception_handler)  # type: ignore[arg-type]
    for exc_class, handler in get_exception_handlers():
        app.add_exception_handler(exc_class, handler)
    app.include_router(apis.router)

    mock_session = AsyncMock()
    mock_db = MagicMock()

    @asynccontextmanager
    async def _fake_session() -> AsyncGenerator[AsyncMock, None]:
        yield mock_session

    mock_db.session = _fake_session
    mock_ctx = MagicMock()
    mock_ctx.registry_db = mock_db

    app.state.ctx = mock_ctx

    _test_identity = Identity(sub="test_user", email="test@test.com", permissions=["org:admin"])
    app.dependency_overrides[resolve_identity] = lambda: _test_identity

    return TestClient(app, headers={"Authorization": "Bearer test-token"})


def test_security_schemes_oauth2(client: TestClient) -> None:
    """Returns OAuth2 scheme with flows."""
    resp_model = SecuritySchemeListResponse(
        data=[
            SecuritySchemeResponse(
                name="oauth2",
                type="oauth2",
                flows=[
                    SecuritySchemeFlowResponse(
                        flow_type="authorizationCode",
                        authorization_url="https://auth.example.com/authorize",
                        token_url="https://auth.example.com/token",
                        refresh_url=None,
                        scopes={"read": "Read access", "write": "Write access"},
                    )
                ],
            )
        ]
    )
    with patch(
        "jentic_one.registry.web.routers.apis.ApiService.get_security_schemes",
        new_callable=AsyncMock,
        return_value=resp_model,
    ):
        resp = client.get("/apis/acme/pets/v1/security-schemes")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 1
    scheme = body["data"][0]
    assert scheme["name"] == "oauth2"
    assert scheme["type"] == "oauth2"
    assert len(scheme["flows"]) == 1
    flow = scheme["flows"][0]
    assert flow["flow_type"] == "authorizationCode"
    assert flow["authorization_url"] == "https://auth.example.com/authorize"
    assert flow["token_url"] == "https://auth.example.com/token"
    assert flow["scopes"] == {"read": "Read access", "write": "Write access"}


def test_security_schemes_404_api_not_found(client: TestClient) -> None:
    """Returns 404 when the API does not exist."""
    with patch(
        "jentic_one.registry.web.routers.apis.ApiService.get_security_schemes",
        new_callable=AsyncMock,
        side_effect=ApiNotFoundError("acme", "pets", "v1"),
    ):
        resp = client.get("/apis/acme/pets/v1/security-schemes")

    assert resp.status_code == 404


def test_security_schemes_404_no_current_revision(client: TestClient) -> None:
    """Returns 404 when the API has no current revision."""
    with patch(
        "jentic_one.registry.web.routers.apis.ApiService.get_security_schemes",
        new_callable=AsyncMock,
        side_effect=NoCurrentRevisionError("acme", "pets", "v1"),
    ):
        resp = client.get("/apis/acme/pets/v1/security-schemes")

    assert resp.status_code == 404


def test_security_schemes_empty(client: TestClient) -> None:
    """Returns empty data when revision has no security schemes."""
    resp_model = SecuritySchemeListResponse(data=[])
    with patch(
        "jentic_one.registry.web.routers.apis.ApiService.get_security_schemes",
        new_callable=AsyncMock,
        return_value=resp_model,
    ):
        resp = client.get("/apis/acme/pets/v1/security-schemes")

    assert resp.status_code == 200
    assert resp.json() == {"data": []}
