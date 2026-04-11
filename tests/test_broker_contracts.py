"""Broker contract tests — route detection and upstream error handling.

These test the broker's HTTP-level behavior using non-routable local
addresses to avoid real network calls. They verify that non-broker
paths return 404, and that broker-like requests to unreachable targets
return error responses rather than succeeding.
"""


def test_broker_requires_dot_in_host(client, agent_key_header):
    """Paths without a dot in the first segment are not broker routes."""
    resp = client.get("/nodotpath/something", headers=agent_key_header)
    assert resp.status_code == 404


def test_broker_no_credentials_returns_error(client, agent_key_header):
    """Broker call to an unknown host returns an error, not a successful proxy."""
    resp = client.get("/127.0.0.2/v1/test", headers=agent_key_header)
    assert resp.status_code >= 400  # must not succeed
    data = resp.json()
    assert "error" in data


def test_broker_unauthenticated_passes_through(client):
    """Broker calls without a key attempt to proxy (upstream auth is upstream's problem).
    With a non-routable target the proxy fails with a connection error.

    Note: The `client` fixture accumulates session cookies from admin_session.
    To make a truly unauthenticated (no toolkit_id) request we must use a
    separate client instance with no cookies.
    """
    from starlette.testclient import TestClient
    from src.main import app as _app
    with TestClient(_app, raise_server_exceptions=False) as anon:
        resp = anon.get("/127.0.0.2/v1/test")
    # Without a key or session, toolkit_id=None, so no credential lookup — broker attempts
    # to proxy and fails with an upstream connection error
    assert resp.status_code in (502, 504), f"Expected proxy error, got {resp.status_code}"
