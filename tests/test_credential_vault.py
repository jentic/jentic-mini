"""Credential vault tests — write-only invariant and CRUD contracts.

The single most important security property: credential values are
accepted on write but NEVER returned on read.
"""
import pytest


def _register_api_with_scheme(client, cookies, api_id, scheme_type="bearer"):
    """Helper: register a minimal API with a security scheme so credentials can be stored."""
    import json as _json

    if scheme_type == "bearer":
        schemes = {"BearerAuth": {"type": "http", "scheme": "bearer"}}
    else:
        schemes = {"ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-Api-Key"}}

    spec = {
        "openapi": "3.1.0",
        "info": {"title": api_id, "version": "1.0.0"},
        "servers": [{"url": f"https://{api_id}"}],
        "components": {"securitySchemes": schemes},
        "paths": {"/test": {"get": {"operationId": "test", "responses": {"200": {"description": "ok"}}}}},
    }

    resp = client.post("/import", cookies=cookies, json={
        "sources": [{
            "type": "inline",
            "content": _json.dumps(spec),
            "filename": f"{api_id}.json",
        }],
    })
    assert resp.status_code in (200, 201), f"Import failed: {resp.text}"


def test_create_credential_returns_id_not_value(client, admin_session):
    """POST /credentials returns metadata but never the plaintext value."""
    api_id = "vault-create.example.com"
    _register_api_with_scheme(client, admin_session, api_id)
    resp = client.post("/credentials", cookies=admin_session, json={
        "label": "Test Bearer Token",
        "value": "sk-secret-test-value-12345",
        "api_id": api_id,
        "auth_type": "bearer",
    })
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    data = resp.json()
    assert "id" in data
    # INVARIANT: value must never appear in the response
    assert "value" not in data
    assert "encrypted_value" not in data
    assert "env_var" not in data


def test_get_credential_never_returns_value(client, admin_session):
    """GET /credentials/{id} must not include the plaintext value."""
    api_id = "vault-read.example.com"
    _register_api_with_scheme(client, admin_session, api_id, "apiKey")
    create_resp = client.post("/credentials", cookies=admin_session, json={
        "label": "Vault Read Test",
        "value": "my-secret-api-key",
        "api_id": api_id,
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


def test_credential_bound_to_api(client, admin_session):
    """Created credential has the correct api_id."""
    api_id = "vault-bound.example.com"
    _register_api_with_scheme(client, admin_session, api_id)
    resp = client.post("/credentials", cookies=admin_session, json={
        "label": "Bound Test",
        "value": "secret",
        "api_id": api_id,
        "auth_type": "bearer",
    })
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    cred_id = resp.json()["id"]
    data = client.get(f"/credentials/{cred_id}", cookies=admin_session).json()
    assert data["api_id"] == api_id
