"""Unit tests for spec download route handlers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jentic.problem_details import ProblemDetailException, problem_detail_exception_handler

from jentic_one.registry.services.errors import (
    ApiNotFoundError,
    NoCurrentRevisionError,
    RevisionNotFoundError,
)
from jentic_one.registry.services.spec_download_service import SpecDocument
from jentic_one.registry.web.app import get_exception_handlers
from jentic_one.registry.web.routers import apis
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


_SAMPLE_SPEC: dict[str, object] = {"openapi": "3.1.0", "info": {"title": "Test API"}}
_DOC = SpecDocument(content=_SAMPLE_SPEC, filename_stem="acme-pets-v1")


def test_json_response_default_accept(client: TestClient) -> None:
    with patch(
        "jentic_one.registry.web.routers.apis.SpecDownloadService.get_live_spec",
        new_callable=AsyncMock,
        return_value=_DOC,
    ):
        resp = client.get("/apis/acme/pets/v1/openapi")

    assert resp.status_code == 200
    assert resp.json() == _SAMPLE_SPEC
    assert "application/json" in resp.headers["content-type"]


def test_yaml_response_openapi_yaml(client: TestClient) -> None:
    with patch(
        "jentic_one.registry.web.routers.apis.SpecDownloadService.get_live_spec",
        new_callable=AsyncMock,
        return_value=_DOC,
    ):
        resp = client.get(
            "/apis/acme/pets/v1/openapi",
            headers={"Accept": "application/openapi+yaml"},
        )

    assert resp.status_code == 200
    assert "application/openapi+yaml" in resp.headers["content-type"]
    assert "openapi:" in resp.text


def test_yaml_response_application_yaml(client: TestClient) -> None:
    with patch(
        "jentic_one.registry.web.routers.apis.SpecDownloadService.get_live_spec",
        new_callable=AsyncMock,
        return_value=_DOC,
    ):
        resp = client.get(
            "/apis/acme/pets/v1/openapi",
            headers={"Accept": "application/yaml"},
        )

    assert resp.status_code == 200
    assert "application/yaml" in resp.headers["content-type"]
    assert "openapi:" in resp.text


def test_406_for_unsupported_accept(client: TestClient) -> None:
    with patch(
        "jentic_one.registry.web.routers.apis.SpecDownloadService.get_live_spec",
        new_callable=AsyncMock,
        return_value=_DOC,
    ):
        resp = client.get(
            "/apis/acme/pets/v1/openapi",
            headers={"Accept": "text/plain"},
        )

    assert resp.status_code == 406


def test_content_disposition_json(client: TestClient) -> None:
    with patch(
        "jentic_one.registry.web.routers.apis.SpecDownloadService.get_live_spec",
        new_callable=AsyncMock,
        return_value=_DOC,
    ):
        resp = client.get("/apis/acme/pets/v1/openapi")

    assert 'filename="acme-pets-v1.json"' in resp.headers["content-disposition"]


def test_content_disposition_yaml(client: TestClient) -> None:
    with patch(
        "jentic_one.registry.web.routers.apis.SpecDownloadService.get_live_spec",
        new_callable=AsyncMock,
        return_value=_DOC,
    ):
        resp = client.get(
            "/apis/acme/pets/v1/openapi",
            headers={"Accept": "application/openapi+yaml"},
        )

    assert 'filename="acme-pets-v1.yaml"' in resp.headers["content-disposition"]


def test_404_for_unknown_api(client: TestClient) -> None:
    with patch(
        "jentic_one.registry.web.routers.apis.SpecDownloadService.get_live_spec",
        new_callable=AsyncMock,
        side_effect=ApiNotFoundError("acme", "missing", "v1"),
    ):
        resp = client.get("/apis/acme/missing/v1/openapi")

    assert resp.status_code == 404


def test_404_for_no_live_revision(client: TestClient) -> None:
    with patch(
        "jentic_one.registry.web.routers.apis.SpecDownloadService.get_live_spec",
        new_callable=AsyncMock,
        side_effect=NoCurrentRevisionError("acme", "pets", "v1"),
    ):
        resp = client.get("/apis/acme/pets/v1/openapi")

    assert resp.status_code == 404


def test_404_for_unknown_revision(client: TestClient) -> None:
    with patch(
        "jentic_one.registry.web.routers.apis.SpecDownloadService.get_revision_spec",
        new_callable=AsyncMock,
        side_effect=RevisionNotFoundError("bad-id", "acme", "pets", "v1"),
    ):
        resp = client.get("/apis/acme/pets/v1/revisions/bad-id/openapi")

    assert resp.status_code == 404


def test_overlays_param_accepted(client: TestClient) -> None:
    with patch(
        "jentic_one.registry.web.routers.apis.SpecDownloadService.get_live_spec",
        new_callable=AsyncMock,
        return_value=_DOC,
    ):
        resp_true = client.get("/apis/acme/pets/v1/openapi?overlays=true")
        resp_false = client.get("/apis/acme/pets/v1/openapi?overlays=false")

    assert resp_true.status_code == 200
    assert resp_false.status_code == 200
    assert resp_true.json() == resp_false.json()
