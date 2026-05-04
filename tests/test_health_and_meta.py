"""Contract tests for /health and /version endpoints."""


def test_health_returns_valid_status(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "setup_required", "account_required")
    assert "version" in data


def test_health_no_auth_required(client):
    """Health endpoint must be accessible without any authentication."""
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_includes_version_string(client):
    data = client.get("/health").json()
    assert isinstance(data["version"], str)
    assert data["version"] == "0.0.0-test"


def test_version_returns_shape(admin_client):
    resp = admin_client.get("/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "current" in data
    assert "latest" in data
    assert "release_url" in data
    assert data["current"] == "0.0.0-test"


def test_version_telemetry_off_returns_null_latest(admin_client):
    """With JENTIC_TELEMETRY=off, latest should be null (no GitHub check)."""
    data = admin_client.get("/version").json()
    assert data["latest"] is None
    assert data["release_url"] is None
