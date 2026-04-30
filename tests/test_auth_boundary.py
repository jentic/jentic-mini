"""Auth perimeter tests — verifies the authentication boundary."""

from starlette.testclient import TestClient


def test_protected_endpoint_returns_401_without_key(app):
    """Protected endpoints must reject unauthenticated requests."""
    # Fresh client: the session-scoped ``client`` may already hold admin cookies
    # from fixtures used by other modules collected earlier (e.g. test_agents_admin).
    with TestClient(app, raise_server_exceptions=False) as anonymous:
        resp = anonymous.get("/toolkits")
    assert resp.status_code == 401


def test_invalid_key_returns_401(app):
    """A bogus API key must be rejected."""
    with TestClient(app, raise_server_exceptions=False) as anonymous:
        resp = anonymous.get("/toolkits", headers={"X-Jentic-API-Key": "tk_bogus_not_real"})
    assert resp.status_code == 401


def test_valid_agent_key_returns_200(client, agent_key_header):
    """A valid agent key grants access to search."""
    resp = client.get("/search?q=test", headers=agent_key_header)
    assert resp.status_code == 200


def test_agent_cannot_create_credentials(client, agent_key_header):
    """Agents cannot create credentials without explicit permission.
    Returns 403 (permission denied) or 409 (no security scheme) — either
    way the credential is NOT created."""
    resp = client.post(
        "/credentials",
        headers=agent_key_header,
        json={
            "label": "test",
            "value": "secret123",
            "api_id": "test.example.com",
            "auth_type": "bearer",
        },
    )
    assert resp.status_code in (403, 409)


def test_human_session_can_access_toolkits(client, admin_session):
    """Human sessions can access protected endpoints."""
    resp = client.get("/toolkits", cookies=admin_session)
    assert resp.status_code == 200


def test_public_paths_no_auth(client):
    """Public paths should work without any authentication."""
    for path in ["/health", "/docs", "/openapi.json"]:
        resp = client.get(path)
        assert resp.status_code in (200, 301, 307), f"{path} returned {resp.status_code}"
