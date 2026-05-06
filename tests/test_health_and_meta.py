"""Contract tests for /health and /version endpoints."""


def test_health_returns_valid_status(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "setup_required")
    assert "version" in data


def test_health_response_shape_matches_status(client):
    """Discriminated union: each ``status`` carries a known shape so SDK
    consumers can switch on the field without guessing.
    """
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()

    if data["status"] == "ok":
        assert isinstance(data["apis_registered"], int)
        assert data["apis_registered"] >= 0
        # Bootstrap fields must NOT appear once the instance is set up.
        for absent in (
            "account_created",
            "setup_url",
            "oauth_authorization_server_metadata",
            "registration_endpoint",
            "token_endpoint",
            "next_step",
            "message",
        ):
            assert absent not in data, f"{absent!r} should not appear in status=ok"
    else:
        assert data["status"] == "setup_required"
        assert data["account_created"] is False
        assert isinstance(data["setup_url"], str)
        assert isinstance(data["registration_endpoint"], str)
        assert isinstance(data["token_endpoint"], str)
        assert isinstance(data["oauth_authorization_server_metadata"], str)


def test_health_in_openapi_spec(client):
    """``/health``'s response schema must be declared so SDK consumers don't
    fall back to ``any``. Previously the route had no response_model.
    """
    spec = client.get("/openapi.json").json()
    health_get = spec["paths"]["/health"]["get"]
    schema_ref = health_get["responses"]["200"]["content"]["application/json"]["schema"]
    # Either a $ref to a named model, a direct anyOf union, or a discriminator
    # block — all acceptable; bare `{}` is not.
    assert schema_ref, "/health response schema must not be empty"
    assert any(key in schema_ref for key in ("$ref", "anyOf", "oneOf")), (
        f"/health response schema is empty / untyped: {schema_ref!r}"
    )


def test_health_no_auth_required(client):
    """Health endpoint must be accessible without any authentication."""
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_includes_version_string(client):
    data = client.get("/health").json()
    assert isinstance(data["version"], str)
    assert data["version"] == "0.0.0-test"


def test_version_returns_shape(admin_client):
    resp = admin_client.get("/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "current" in data
    assert "latest" in data
    assert "release_url" in data
    assert data["current"] == "0.0.0-test"


def test_version_telemetry_off_returns_null_latest(admin_client):
    """With JENTIC_TELEMETRY=off, latest should be null (no GitHub check)."""
    data = admin_client.get("/version").json()
    assert data["latest"] is None
    assert data["release_url"] is None
