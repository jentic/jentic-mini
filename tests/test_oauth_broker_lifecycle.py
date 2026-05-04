"""OAuth broker lifecycle tests — CRUD, account management, auth boundary.

Tests the HTTP-level behavior of broker CRUD, account management,
and reconnect endpoints. No live Pipedream connection — these verify
auth, validation, and error responses only.
"""

import pytest


BROKER_ID = "test-oauth-broker"


@pytest.fixture(scope="module")
def broker(admin_client):
    """Create a test broker for the module. Cleaned up at the end."""
    resp = admin_client.post(
        "/oauth-brokers",
        json={
            "id": BROKER_ID,
            "type": "pipedream",
            "config": {
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "project_id": "proj_test123",
            },
        },
    )
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    yield BROKER_ID
    admin_client.delete(f"/oauth-brokers/{BROKER_ID}")


# ── PATCH /oauth-brokers/{id} ────────────────────────────────────────────────


def test_update_broker_requires_human_session(agent_only_client, broker):
    """Agent keys cannot update broker config."""
    resp = agent_only_client.patch(
        f"/oauth-brokers/{broker}",
        json={
            "config": {"client_id": "new-id"},
        },
    )
    assert resp.status_code == 403


def test_update_broker_404_nonexistent(admin_client):
    """Updating a nonexistent broker returns 404."""
    resp = admin_client.patch(
        "/oauth-brokers/nonexistent",
        json={
            "config": {"client_id": "new-id"},
        },
    )
    assert resp.status_code == 404


def test_update_broker_success(admin_client, broker):
    """PATCH updates broker config fields."""
    resp = admin_client.patch(
        f"/oauth-brokers/{broker}",
        json={
            "config": {"client_id": "updated-client-id"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["config"]["client_id"] == "updated-client-id"


# ── PATCH /oauth-brokers/{id}/accounts/{account_id} ─────────────────────────


def test_rename_account_requires_human_session(agent_only_client, broker):
    """Agent keys cannot rename accounts."""
    resp = agent_only_client.patch(
        f"/oauth-brokers/{broker}/accounts/apn_test",
        json={"label": "new name"},
    )
    assert resp.status_code == 403


def test_rename_account_404_nonexistent(admin_client, broker):
    """Renaming a nonexistent account returns 404."""
    resp = admin_client.patch(
        f"/oauth-brokers/{broker}/accounts/apn_nonexistent",
        json={"label": "new name"},
    )
    assert resp.status_code == 404


def test_rename_account_rejects_empty_label(admin_client, broker):
    """Empty label is rejected with 422 (Pydantic validation)."""
    resp = admin_client.patch(
        f"/oauth-brokers/{broker}/accounts/apn_test",
        json={"label": ""},
    )
    assert resp.status_code == 422


# ── POST /oauth-brokers/{id}/connect-link ─────────────────────────────────────


def test_connect_link_rejects_empty_label(admin_client, broker):
    """Empty label is rejected with 422 (min_length=1 validation)."""
    resp = admin_client.post(
        f"/oauth-brokers/{broker}/connect-link",
        json={"app": "google_calendar", "label": ""},
    )
    assert resp.status_code == 422


# ── POST /oauth-brokers/{id}/accounts/{account_id}/reconnect-link ───────────


def test_reconnect_link_requires_human_session(agent_only_client, broker):
    """Agent keys cannot generate reconnect links."""
    resp = agent_only_client.post(
        f"/oauth-brokers/{broker}/accounts/apn_test/reconnect-link",
    )
    assert resp.status_code == 403


def test_reconnect_link_404_nonexistent_account(admin_client, broker):
    """Reconnect for a nonexistent account returns 404."""
    resp = admin_client.post(
        f"/oauth-brokers/{broker}/accounts/apn_nonexistent/reconnect-link",
    )
    assert resp.status_code == 404


# ── DELETE /oauth-brokers/{id}/accounts/{account_id} ─────────────────────────


def test_delete_account_requires_human_session(agent_only_client, broker):
    """Agent keys cannot delete connected accounts."""
    resp = agent_only_client.delete(f"/oauth-brokers/{broker}/accounts/apn_test")
    assert resp.status_code == 403


# ── DELETE /oauth-brokers/{id} ───────────────────────────────────────────────


def test_delete_broker_requires_human_session(agent_only_client, broker):
    """Agent keys cannot delete brokers."""
    resp = agent_only_client.delete(f"/oauth-brokers/{broker}")
    assert resp.status_code == 403


def test_delete_broker_404_nonexistent(admin_client):
    """Deleting a nonexistent broker returns 404."""
    resp = admin_client.delete("/oauth-brokers/nonexistent")
    assert resp.status_code == 404


def test_delete_broker_success(admin_client, broker):
    """Deleting a broker removes it and returns success."""
    resp = admin_client.delete(f"/oauth-brokers/{broker}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is True

    # Verify it's gone
    resp = admin_client.get(f"/oauth-brokers/{broker}")
    assert resp.status_code == 404
