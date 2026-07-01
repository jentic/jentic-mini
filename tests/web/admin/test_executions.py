"""Web tests for the admin executions router."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_list_success(authed_client: TestClient) -> None:
    resp = authed_client.get("/executions")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "has_more" in data


def test_list_default_limit(authed_client: TestClient) -> None:
    resp = authed_client.get("/executions")
    assert resp.status_code == 200


def test_list_limit_max_100(authed_client: TestClient) -> None:
    resp = authed_client.get("/executions?limit=101")
    assert resp.status_code == 422


def test_list_with_terminal_status_filter(authed_client: TestClient) -> None:
    resp = authed_client.get("/executions?status=completed&toolkit_id=tk-1")
    assert resp.status_code == 200


def test_list_rejects_non_terminal_status(authed_client: TestClient) -> None:
    resp = authed_client.get("/executions?status=running")
    assert resp.status_code == 422


def test_list_with_api_filter(authed_client: TestClient) -> None:
    resp = authed_client.get("/executions?api=stripe:payments:v1")
    assert resp.status_code == 200


def test_list_with_from_to_filters(authed_client: TestClient) -> None:
    resp = authed_client.get("/executions?from=2024-01-01T00:00:00Z&to=2024-12-31T00:00:00Z")
    assert resp.status_code == 200


def test_list_without_auth(unauthed_client: TestClient) -> None:
    resp = unauthed_client.get("/executions")
    assert resp.status_code == 401


def test_get_not_found(authed_client: TestClient) -> None:
    resp = authed_client.get("/executions/nonexistent-exec-id")
    assert resp.status_code == 404
    assert resp.json()["type"] == "execution_not_found"
