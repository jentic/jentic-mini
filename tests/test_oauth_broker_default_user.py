"""OAuth broker default_external_user_id tests.

Verifies that POST /oauth-brokers correctly persists and returns the
default_external_user_id from config, and that the value is not silently
overridden with the hardcoded string "default".
"""

import pytest


BROKER_CUSTOM_USER = "test-oauth-broker-custom-user"
BROKER_DEFAULT_USER = "test-oauth-broker-default-user"

_BASE_CONFIG = {
    "client_id": "test-client-id",
    "client_secret": "test-client-secret",
    "project_id": "proj_test123",
}


@pytest.fixture(scope="module")
def broker_with_custom_user(client, admin_session):
    resp = client.post(
        "/oauth-brokers",
        cookies=admin_session,
        json={
            "id": BROKER_CUSTOM_USER,
            "type": "pipedream",
            "config": {**_BASE_CONFIG, "default_external_user_id": "alice"},
        },
    )
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    yield BROKER_CUSTOM_USER
    client.delete(f"/oauth-brokers/{BROKER_CUSTOM_USER}", cookies=admin_session)


@pytest.fixture(scope="module")
def broker_with_default_user(client, admin_session):
    resp = client.post(
        "/oauth-brokers",
        cookies=admin_session,
        json={
            "id": BROKER_DEFAULT_USER,
            "type": "pipedream",
            "config": _BASE_CONFIG,
        },
    )
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    yield BROKER_DEFAULT_USER
    client.delete(f"/oauth-brokers/{BROKER_DEFAULT_USER}", cookies=admin_session)


def test_custom_default_external_user_id_is_persisted(client, admin_session, broker_with_custom_user):
    """default_external_user_id from config must be stored and returned, not overridden with 'default'."""
    resp = client.get(f"/oauth-brokers/{broker_with_custom_user}", cookies=admin_session)
    assert resp.status_code == 200, f"GET failed: {resp.text}"
    data = resp.json()
    assert data["config"]["default_external_user_id"] == "alice", (
        f"Expected 'alice', got {data['config'].get('default_external_user_id')!r} — "
        "backend is overriding the provided value with 'default'"
    )


def test_omitted_default_external_user_id_falls_back_to_default(client, admin_session, broker_with_default_user):
    """When default_external_user_id is omitted from config, it should fall back to 'default'."""
    resp = client.get(f"/oauth-brokers/{broker_with_default_user}", cookies=admin_session)
    assert resp.status_code == 200, f"GET failed: {resp.text}"
    data = resp.json()
    assert data["config"]["default_external_user_id"] == "default", (
        f"Expected 'default' fallback, got {data['config'].get('default_external_user_id')!r}"
    )
