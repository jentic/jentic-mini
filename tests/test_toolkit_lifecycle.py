"""Toolkit lifecycle tests — CRUD, key management, credential counts.

Includes regression tests for #60 (toolkit list showing wrong counts).
"""


def test_default_toolkit_exists(admin_client):
    """The default toolkit is always present after DB init."""
    resp = admin_client.get("/toolkits/default")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "default"
    assert data["name"] == "Default"


def test_toolkit_list_returns_array(admin_client):
    """GET /toolkits returns a list."""
    resp = admin_client.get("/toolkits")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_toolkit_list_includes_counts(admin_client):
    """Each toolkit in the list has key_count and credential_count (regression #60)."""
    resp = admin_client.get("/toolkits")
    assert resp.status_code == 200
    for toolkit in resp.json():
        assert "key_count" in toolkit, f"Toolkit {toolkit['id']} missing key_count"
        assert "credential_count" in toolkit, f"Toolkit {toolkit['id']} missing credential_count"


def test_default_toolkit_counts_all_credentials(admin_client):
    """Default toolkit credential_count matches total credentials (regression #60).

    The default toolkit implicitly owns ALL credentials, not just
    those explicitly bound via toolkit_credentials.
    """
    # Get total credential count
    creds_resp = admin_client.get("/credentials")
    assert creds_resp.status_code == 200
    total_creds = len(creds_resp.json())

    # Get default toolkit's reported count
    toolkits_resp = admin_client.get("/toolkits")
    default = next(t for t in toolkits_resp.json() if t["id"] == "default")
    assert default["credential_count"] == total_creds


def test_create_and_list_key(admin_client):
    """POST /toolkits/{id}/keys creates a key, GET lists it."""
    # Create a key
    resp = admin_client.post(
        "/toolkits/default/keys",
        json={
            "label": "test-key",
        },
    )
    assert resp.status_code in (200, 201), f"Key creation failed: {resp.text}"
    data = resp.json()
    assert "key" in data  # The raw key is returned once

    # List keys — verify the created key appears
    keys_resp = admin_client.get("/toolkits/default/keys")
    assert keys_resp.status_code == 200
    keys_data = keys_resp.json()
    key_labels = [k["label"] for k in keys_data["keys"]]
    assert "test-key" in key_labels
