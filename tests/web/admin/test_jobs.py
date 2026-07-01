"""Web tests for the admin jobs router."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_list_success(authed_client: TestClient) -> None:
    resp = authed_client.get("/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "has_more" in data


def test_list_default_limit(authed_client: TestClient) -> None:
    resp = authed_client.get("/jobs")
    assert resp.status_code == 200


def test_list_without_auth(unauthed_client: TestClient) -> None:
    resp = unauthed_client.get("/jobs")
    assert resp.status_code == 401


def test_get_not_found(authed_client: TestClient) -> None:
    resp = authed_client.get("/jobs/nonexistent-job-id")
    assert resp.status_code == 404


def test_get_result_not_found(authed_client: TestClient) -> None:
    resp = authed_client.get("/jobs/nonexistent-job-id/result")
    assert resp.status_code == 404 or resp.status_code == 409


def test_list_filter_by_status(authed_client: TestClient) -> None:
    resp = authed_client.get("/jobs?status=queued&status=running")
    assert resp.status_code == 200


def test_list_filter_from_to(authed_client: TestClient) -> None:
    resp = authed_client.get("/jobs?from=2026-01-01T00:00:00Z&to=2026-12-31T00:00:00Z")
    assert resp.status_code == 200


def test_list_limit_max_100(authed_client: TestClient) -> None:
    resp = authed_client.get("/jobs?limit=101")
    assert resp.status_code == 422
