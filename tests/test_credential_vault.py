"""Credential vault tests — write-only invariant and CRUD contracts.

The single most important security property: credential values are
accepted on write but NEVER returned on read.
"""


def test_create_credential_returns_id_not_value(client, admin_session):
    """POST /credentials returns metadata but never the plaintext value."""
    resp = client.post("/credentials", cookies=admin_session, json={
        "label": "Test Bearer Token",
        "value": "sk-secret-test-value-12345",
        "routes": ["vault-create.example.com"],
        "auth_type": "bearer",
    })
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    data = resp.json()
    assert "id" in data
    assert data["id"] == "test-bearer-token"  # slug from label
    # INVARIANT: value must never appear in the response
    assert "value" not in data
    assert "encrypted_value" not in data
    assert "env_var" not in data


def test_get_credential_never_returns_value(client, admin_session):
    """GET /credentials/{id} must not include the plaintext value."""
    create_resp = client.post("/credentials", cookies=admin_session, json={
        "label": "Vault Read Test",
        "value": "my-secret-api-key",
        "routes": ["vault-read.example.com"],
        "auth_type": "apiKey",
    })
    assert create_resp.status_code in (200, 201), f"Create failed: {create_resp.text}"
    cred_id = create_resp.json()["id"]

    resp = client.get(f"/credentials/{cred_id}", cookies=admin_session)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == cred_id
    assert data["label"] == "Vault Read Test"
    # INVARIANT: value never returned
    assert "value" not in data
    assert "encrypted_value" not in data


def test_list_credentials_never_returns_values(client, admin_session):
    """GET /credentials must not include values on any item."""
    resp = client.get("/credentials", cookies=admin_session)
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    for item in items:
        assert "value" not in item
        assert "encrypted_value" not in item


def test_credential_has_routes(client, admin_session):
    """Created credential has the correct routes."""
    resp = client.post("/credentials", cookies=admin_session, json={
        "label": "Routes Test",
        "value": "secret",
        "routes": ["vault-routes.example.com/api"],
        "auth_type": "bearer",
    })
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    cred_id = resp.json()["id"]
    data = client.get(f"/credentials/{cred_id}", cookies=admin_session).json()
    assert data["routes"] == ["vault-routes.example.com/api"]
