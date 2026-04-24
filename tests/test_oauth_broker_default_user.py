"""OAuth broker default_external_user_id tests.

Verifies that POST /oauth-brokers correctly persists and returns the
default_external_user_id from config, and that the value is passed
to discover_accounts on creation rather than being silently overridden
with the hardcoded string "default".
"""

import pytest

from src.brokers.pipedream import PipedreamOAuthBroker


BROKER_CUSTOM_USER = "test-oauth-broker-custom-user"
BROKER_DEFAULT_USER = "test-oauth-broker-default-user"

_BASE_CONFIG = {
    "client_id": "test-client-id",
    "client_secret": "test-client-secret",
    "project_id": "proj_test123",
}


@pytest.fixture(scope="module")
def broker_with_custom_user(admin_client):
    resp = admin_client.post(
        "/oauth-brokers",
        json={
            "id": BROKER_CUSTOM_USER,
            "type": "pipedream",
            "config": {**_BASE_CONFIG, "default_external_user_id": "alice"},
        },
    )
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    yield BROKER_CUSTOM_USER
    admin_client.delete(f"/oauth-brokers/{BROKER_CUSTOM_USER}")


@pytest.fixture(scope="module")
def broker_with_default_user(admin_client):
    resp = admin_client.post(
        "/oauth-brokers",
        json={
            "id": BROKER_DEFAULT_USER,
            "type": "pipedream",
            "config": _BASE_CONFIG,
        },
    )
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    yield BROKER_DEFAULT_USER
    admin_client.delete(f"/oauth-brokers/{BROKER_DEFAULT_USER}")


def test_custom_default_external_user_id_is_persisted(admin_client, broker_with_custom_user):
    """default_external_user_id from config must be stored and returned, not overridden with 'default'."""
    resp = admin_client.get(f"/oauth-brokers/{broker_with_custom_user}")
    assert resp.status_code == 200, f"GET failed: {resp.text}"
    data = resp.json()
    assert data["config"]["default_external_user_id"] == "alice", (
        f"Expected 'alice', got {data['config'].get('default_external_user_id')!r} -- "
        "backend is overriding the provided value with 'default'"
    )


def test_omitted_default_external_user_id_falls_back_to_default(admin_client, broker_with_default_user):
    """When default_external_user_id is omitted from config, it should fall back to 'default'."""
    resp = admin_client.get(f"/oauth-brokers/{broker_with_default_user}")
    assert resp.status_code == 200, f"GET failed: {resp.text}"
    data = resp.json()
    assert data["config"]["default_external_user_id"] == "default", (
        f"Expected 'default' fallback, got {data['config'].get('default_external_user_id')!r}"
    )


def test_discover_accounts_called_with_configured_user_id(admin_client, monkeypatch):
    """discover_accounts on create must receive the caller-supplied value, not 'default'."""
    broker_id = "test-oauth-broker-discover-spy"
    calls = []

    async def spy(self, external_user_id: str) -> int:
        calls.append(external_user_id)
        return 0

    monkeypatch.setattr(PipedreamOAuthBroker, "discover_accounts", spy)

    resp = admin_client.post(
        "/oauth-brokers",
        json={
            "id": broker_id,
            "type": "pipedream",
            "config": {**_BASE_CONFIG, "default_external_user_id": "alice"},
        },
    )
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    admin_client.delete(f"/oauth-brokers/{broker_id}")

    assert calls == ["alice"], (
        f"discover_accounts was called with {calls!r}; expected ['alice'] -- "
        "the configured default_external_user_id is not being forwarded to the initial sync"
    )
