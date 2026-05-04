"""Credential vault tests — write-only invariant and CRUD contracts.

The single most important security property: credential values are
accepted on write but NEVER returned on read.
"""

import json


def _register_api_with_scheme(client, api_id, scheme_type="bearer"):
    """Helper: register a minimal API with a security scheme so credentials can be stored."""

    if scheme_type == "bearer":
        schemes = {"BearerAuth": {"type": "http", "scheme": "bearer"}}
    else:
        schemes = {"ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-Api-Key"}}

    spec = {
        "openapi": "3.1.0",
        "info": {"title": api_id, "version": "1.0.0"},
        "servers": [{"url": f"https://{api_id}"}],
        "components": {"securitySchemes": schemes},
        "paths": {
            "/test": {"get": {"operationId": "test", "responses": {"200": {"description": "ok"}}}}
        },
    }

    resp = client.post(
        "/import",
        json={
            "sources": [
                {
                    "type": "inline",
                    "content": json.dumps(spec),
                    "filename": f"{api_id}.json",
                }
            ],
        },
    )
    assert resp.status_code in (200, 201), f"Import failed: {resp.text}"


def test_create_credential_returns_id_not_value(admin_client):
    """POST /credentials returns metadata but never the plaintext value."""
    api_id = "vault-create.example.com"
    _register_api_with_scheme(admin_client, api_id)
    resp = admin_client.post(
        "/credentials",
        json={
            "label": "Test Bearer Token",
            "value": "sk-secret-test-value-12345",
            "api_id": api_id,
            "auth_type": "bearer",
        },
    )
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    data = resp.json()
    assert "id" in data
    # INVARIANT: value must never appear in the response
    assert "value" not in data
    assert "encrypted_value" not in data
    assert "env_var" not in data


def test_get_credential_never_returns_value(admin_client):
    """GET /credentials/{id} must not include the plaintext value."""
    api_id = "vault-read.example.com"
    _register_api_with_scheme(admin_client, api_id, "apiKey")
    create_resp = admin_client.post(
        "/credentials",
        json={
            "label": "Vault Read Test",
            "value": "my-secret-api-key",
            "api_id": api_id,
            "auth_type": "apiKey",
        },
    )
    assert create_resp.status_code in (200, 201), f"Create failed: {create_resp.text}"
    cred_id = create_resp.json()["id"]

    resp = admin_client.get(f"/credentials/{cred_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == cred_id
    assert data["label"] == "Vault Read Test"
    # INVARIANT: value never returned
    assert "value" not in data
    assert "encrypted_value" not in data


def test_list_credentials_never_returns_values(admin_client):
    """GET /credentials must not include values on any item."""
    resp = admin_client.get("/credentials")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    for item in items:
        assert "value" not in item
        assert "encrypted_value" not in item


def test_credential_bound_to_api(admin_client):
    """Created credential has the correct api_id."""
    api_id = "vault-bound.example.com"
    _register_api_with_scheme(admin_client, api_id)
    resp = admin_client.post(
        "/credentials",
        json={
            "label": "Bound Test",
            "value": "secret",
            "api_id": api_id,
            "auth_type": "bearer",
        },
    )
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    cred_id = resp.json()["id"]
    data = admin_client.get(f"/credentials/{cred_id}").json()
    assert data["api_id"] == api_id


def test_create_no_auth_credential_skips_scheme_check(admin_client):
    """auth_type=none credentials should not require a security scheme or overlay."""
    api_id = "noauth-local.example.com"

    # Register a bare API with NO security schemes
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "No-Auth API", "version": "1.0.0"},
        "servers": [{"url": f"https://{api_id}"}],
        "paths": {
            "/health": {
                "get": {"operationId": "health", "responses": {"200": {"description": "ok"}}}
            }
        },
    }
    resp = admin_client.post(
        "/import",
        json={
            "sources": [
                {"type": "inline", "content": json.dumps(spec), "filename": f"{api_id}.json"}
            ],
        },
    )
    assert resp.status_code in (200, 201), f"Import failed: {resp.text}"

    # Creating a credential with auth_type=none should succeed (not 409)
    resp = admin_client.post(
        "/credentials",
        json={
            "label": "No-Auth Local Service",
            "value": "",
            "api_id": api_id,
            "auth_type": "none",
        },
    )
    assert resp.status_code in (200, 201), (
        f"Expected 201 for auth_type=none, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data["auth_type"] == "none"


def test_create_credential_without_scheme_still_blocked(admin_client):
    """Regular auth_type credentials for APIs without schemes should still get 409."""
    api_id = "noscheme-blocked.example.com"

    # Register a bare API with NO security schemes
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "No-Scheme API", "version": "1.0.0"},
        "servers": [{"url": f"https://{api_id}"}],
        "paths": {
            "/data": {
                "get": {"operationId": "getData", "responses": {"200": {"description": "ok"}}}
            }
        },
    }
    resp = admin_client.post(
        "/import",
        json={
            "sources": [
                {"type": "inline", "content": json.dumps(spec), "filename": f"{api_id}.json"}
            ],
        },
    )
    assert resp.status_code in (200, 201), f"Import failed: {resp.text}"

    # Creating a bearer credential should fail with 409 (no security scheme)
    resp = admin_client.post(
        "/credentials",
        json={
            "label": "Should Fail",
            "value": "some-token",
            "api_id": api_id,
            "auth_type": "bearer",
        },
    )
    assert resp.status_code == 409, (
        f"Expected 409 for bearer without scheme, got {resp.status_code}: {resp.text}"
    )
