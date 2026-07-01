"""Web tests for the admin health endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_health_returns_200(unauthed_client: TestClient) -> None:
    resp = unauthed_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["surface"] == "admin"
    assert "setup_required" in data
