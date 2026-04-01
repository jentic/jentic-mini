"""Broker contract tests — credential injection, policy gate, fail-closed.

These test the broker's HTTP-level behavior. They don't call upstream
APIs (no network) — they verify the broker's own responses when
credentials are missing, policies deny, or errors occur.
"""


def test_broker_requires_dot_in_host(client, agent_key_header):
    """Paths without a dot in the first segment are not broker routes."""
    resp = client.get("/nodotpath/something", headers=agent_key_header)
    assert resp.status_code == 404


def test_broker_no_credentials_returns_error(client, agent_key_header):
    """Broker call to an unknown host returns an error, not a successful proxy."""
    resp = client.get("/api.unknown-test-host.com/v1/test", headers=agent_key_header)
    assert resp.status_code >= 400  # must not succeed
    data = resp.json()
    assert "error" in data


def test_broker_unauthenticated_passes_through(client):
    """Broker calls without a key pass through (upstream auth is upstream's problem).
    The broker should still attempt to proxy, not return 401."""
    resp = client.get("/api.unknown-test-host.com/v1/test")
    # Without a key, no toolkit_id, so no credential lookup — should try to proxy
    # and fail on the network side (connection refused or similar)
    assert resp.status_code in (500, 502, 504), f"Expected proxy error, got {resp.status_code}"
