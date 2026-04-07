"""Toolkit lifecycle tests — CRUD, key management, credential counts.

Includes regression tests for #60 (toolkit list showing wrong counts).
"""


def test_default_toolkit_exists(client, admin_session):
    """The default toolkit is always present after DB init."""
    resp = client.get("/toolkits/default", cookies=admin_session)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "default"
    assert data["name"] == "Default"


def test_toolkit_list_returns_array(client, admin_session):
    """GET /toolkits returns a list."""
    resp = client.get("/toolkits", cookies=admin_session)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_toolkit_list_includes_counts(client, admin_session):
    """Each toolkit in the list has key_count and credential_count (regression #60)."""
    resp = client.get("/toolkits", cookies=admin_session)
    assert resp.status_code == 200
    for toolkit in resp.json():
        assert "key_count" in toolkit, f"Toolkit {toolkit['id']} missing key_count"
        assert "credential_count" in toolkit, f"Toolkit {toolkit['id']} missing credential_count"


def test_default_toolkit_counts_all_credentials(client, admin_session):
    """Default toolkit credential_count matches total credentials (regression #60).

    The default toolkit implicitly owns ALL credentials, not just
    those explicitly bound via toolkit_credentials.
    """
    # Get total credential count
    creds_resp = client.get("/credentials", cookies=admin_session)
    assert creds_resp.status_code == 200
    total_creds = len(creds_resp.json())

    # Get default toolkit's reported count
    toolkits_resp = client.get("/toolkits", cookies=admin_session)
    default = next(t for t in toolkits_resp.json() if t["id"] == "default")
    assert default["credential_count"] == total_creds


def test_create_and_list_key(client, admin_session):
    """POST /toolkits/{id}/keys creates a key, GET lists it."""
    # Create a key
    resp = client.post("/toolkits/default/keys", cookies=admin_session, json={
        "label": "test-key",
    })
    assert resp.status_code in (200, 201), f"Key creation failed: {resp.text}"
    data = resp.json()
    assert "key" in data  # The raw key is returned once

    # List keys — verify the created key appears
    keys_resp = client.get("/toolkits/default/keys", cookies=admin_session)
    assert keys_resp.status_code == 200
    keys_data = keys_resp.json()
    key_labels = [k["label"] for k in keys_data["keys"]]
    assert "test-key" in key_labels
