"""OAuth broker lifecycle tests — CRUD, account management, auth boundary.

Tests the HTTP-level behavior of broker CRUD, account management,
and reconnect endpoints. No live Pipedream connection — these verify
auth, validation, and error responses only.
"""
import pytest
from starlette.testclient import TestClient


BROKER_ID = "test-oauth-broker"


@pytest.fixture()
def broker(client, admin_session):
    """Create a test broker. Cleaned up after each test that uses it."""
    resp = client.post("/oauth-brokers", cookies=admin_session, json={
        "id": BROKER_ID,
        "type": "pipedream",
        "config": {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "project_id": "proj_test123",
        },
    })
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    yield BROKER_ID
    client.delete(f"/oauth-brokers/{BROKER_ID}", cookies=admin_session)


@pytest.fixture()
def agent_only_client(app, agent_key):
    """A fresh TestClient with no session cookies — only agent key auth."""
    with TestClient(app, raise_server_exceptions=False) as c:
        c.headers["X-Jentic-API-Key"] = agent_key
        yield c


# ── PATCH /oauth-brokers/{id} ────────────────────────────────────────────────

def test_update_broker_requires_human_session(agent_only_client, broker):
    """Agent keys cannot update broker config."""
    resp = agent_only_client.patch(f"/oauth-brokers/{broker}", json={
        "config": {"client_id": "new-id"},
    })
    assert resp.status_code == 403


def test_update_broker_404_nonexistent(client, admin_session):
    """Updating a nonexistent broker returns 404."""
    resp = client.patch("/oauth-brokers/nonexistent", cookies=admin_session, json={
        "config": {"client_id": "new-id"},
    })
    assert resp.status_code == 404


def test_update_broker_success(client, admin_session, broker):
    """PATCH updates broker config fields."""
    resp = client.patch(f"/oauth-brokers/{broker}", cookies=admin_session, json={
        "config": {"client_id": "updated-client-id"},
    })
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


def test_rename_account_404_nonexistent(client, admin_session, broker):
    """Renaming a nonexistent account returns 404."""
    resp = client.patch(
        f"/oauth-brokers/{broker}/accounts/apn_nonexistent",
        cookies=admin_session,
        json={"label": "new name"},
    )
    assert resp.status_code == 404


def test_rename_account_rejects_empty_label(client, admin_session, broker):
    """Empty label is rejected with 422 (Pydantic validation)."""
    resp = client.patch(
        f"/oauth-brokers/{broker}/accounts/apn_test",
        cookies=admin_session,
        json={"label": ""},
    )
    assert resp.status_code == 422


# ── POST /oauth-brokers/{id}/accounts/{account_id}/reconnect-link ───────────

def test_reconnect_link_requires_human_session(agent_only_client, broker):
    """Agent keys cannot generate reconnect links."""
    resp = agent_only_client.post(
        f"/oauth-brokers/{broker}/accounts/apn_test/reconnect-link",
    )
    assert resp.status_code == 403


def test_reconnect_link_404_nonexistent_account(client, admin_session, broker):
    """Reconnect for a nonexistent account returns 404."""
    resp = client.post(
        f"/oauth-brokers/{broker}/accounts/apn_nonexistent/reconnect-link",
        cookies=admin_session,
    )
    assert resp.status_code == 404


# ── DELETE /oauth-brokers/{id} ───────────────────────────────────────────────

def test_delete_broker_requires_human_session(agent_only_client, broker):
    """Agent keys cannot delete brokers."""
    resp = agent_only_client.delete(f"/oauth-brokers/{broker}")
    assert resp.status_code == 403


def test_delete_broker_404_nonexistent(client, admin_session):
    """Deleting a nonexistent broker returns 404."""
    resp = client.delete("/oauth-brokers/nonexistent", cookies=admin_session)
    assert resp.status_code == 404


def test_delete_broker_success(client, admin_session, broker):
    """Deleting a broker removes it and returns success."""
    resp = client.delete(f"/oauth-brokers/{broker}", cookies=admin_session)
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is True

    # Verify it's gone
    resp = client.get(f"/oauth-brokers/{broker}", cookies=admin_session)
    assert resp.status_code == 404
