"""OpenAPI specification contract tests.

Uses Schemathesis to validate API responses match the OpenAPI spec,
plus custom tests for Jentic-specific requirements.
"""

import json
from pathlib import Path


# ────────────────────────────────────────────────────────────────
# 1. Critical: ui/openapi.json matches served spec
# ────────────────────────────────────────────────────────────────


def test_ui_openapi_matches_served_spec(client):
    """The static ui/openapi.json MUST match what /openapi.json serves.

    This ensures the committed file stays in sync with the implementation.
    Fails if someone changes the API without regenerating the static file.
    """
    # Get served spec
    served = client.get("/openapi.json").json()

    # Read committed file
    ui_spec_path = Path(__file__).parent.parent / "ui" / "openapi.json"
    with open(ui_spec_path) as f:
        committed = json.load(f)

    # Compare while ignoring only info.version (which may differ in dev)
    served_normalized = dict(served)
    committed_normalized = dict(committed)

    # Remove version from info but keep rest of info object
    if "info" in served_normalized:
        served_info = dict(served_normalized["info"])
        served_info.pop("version", None)
        served_normalized["info"] = served_info

    if "info" in committed_normalized:
        committed_info = dict(committed_normalized["info"])
        committed_info.pop("version", None)
        committed_normalized["info"] = committed_info

    assert served_normalized == committed_normalized, (
        "ui/openapi.json is out of sync with served spec. "
        "Run: curl http://localhost:8900/openapi.json | python3 -m json.tool > ui/openapi.json"
    )


# ────────────────────────────────────────────────────────────────
# 2. Schemathesis: Auto-validate all responses match schemas
# ────────────────────────────────────────────────────────────────

# Note: Schemathesis pytest integration doesn't work cleanly with FastAPI
# TestClient. Use CLI approach in CI instead (see below).


# ────────────────────────────────────────────────────────────────
# 3. Jentic-specific requirements (Phase 1)
# ────────────────────────────────────────────────────────────────


class TestJenticRequirements:
    """Custom tests for Jentic-specific OpenAPI requirements."""

    def test_servers_https_first(self, client):
        """First server MUST be HTTPS (Phase 1 requirement)."""
        spec = client.get("/openapi.json").json()
        assert spec["servers"][0]["url"].startswith("https://")

    def test_info_has_contact_and_license(self, client):
        """info.contact and info.license MUST be present (Phase 1)."""
        spec = client.get("/openapi.json").json()
        info = spec["info"]

        assert "contact" in info
        assert info["contact"]["name"]
        assert info["contact"]["url"]

        assert "license" in info
        assert info["license"]["name"] == "Apache 2.0"
        assert info["license"]["identifier"] == "Apache-2.0"

    def test_public_endpoints_have_empty_security(self, client):
        """Public endpoints MUST have security: [] (Phase 1)."""
        spec = client.get("/openapi.json").json()

        public_ops = [("/health", "get"), ("/search", "get"), ("/apis", "get")]

        for path, method in public_ops:
            if path in spec["paths"] and method in spec["paths"][path]:
                op = spec["paths"][path][method]
                assert "security" in op, f"{method.upper()} {path} missing security"
                assert op["security"] == [], f"{method.upper()} {path} should be public"

    def test_protected_endpoints_have_explicit_security(self, client):
        """Protected endpoints MUST have explicit security (Phase 1)."""
        spec = client.get("/openapi.json").json()

        protected_ops = [("/credentials", "get"), ("/toolkits", "get")]

        for path, method in protected_ops:
            if path in spec["paths"] and method in spec["paths"][path]:
                op = spec["paths"][path][method]
                assert "security" in op, f"{method.upper()} {path} missing security"
                assert len(op["security"]) > 0, f"{method.upper()} {path} should be protected"

    def test_high_priority_schemas_have_descriptions(self, client):
        """High-priority schemas MUST have descriptions (Phase 1)."""
        spec = client.get("/openapi.json").json()
        schemas = spec["components"]["schemas"]

        priority = ["ApiListPage", "ToolkitOut", "CredentialOut"]

        for schema_name in priority:
            if schema_name in schemas:
                assert "description" in schemas[schema_name], f"{schema_name} missing description"

    def test_token_request_schema_valid(self, client):
        """OAuth2 token endpoint request schema MUST be properly defined and referenced."""
        spec = client.get("/openapi.json").json()
        schemas = spec["components"]["schemas"]

        # Check /user/token endpoint
        token_op = spec["paths"]["/user/token"]["post"]
        req_body = token_op.get("requestBody", {})
        form_schema = (
            req_body.get("content", {})
            .get("application/x-www-form-urlencoded", {})
            .get("schema", {})
        )

        # Should have a schema reference
        assert "$ref" in form_schema or "type" in form_schema, "Token endpoint must have a schema"

        # If it uses a $ref, that schema must exist
        if "$ref" in form_schema:
            ref = form_schema["$ref"]
            schema_name = ref.split("/")[-1]
            assert schema_name in schemas, (
                f"Referenced schema '{schema_name}' must exist in components/schemas"
            )

            # The schema should have required OAuth2 fields
            schema_def = schemas[schema_name]
            props = schema_def.get("properties", {})
            assert "username" in props, "OAuth2 form must have username field"
            assert "password" in props, "OAuth2 form must have password field"

    def test_agent_operations_have_hints(self, client):
        """Agent-facing operations SHOULD have x-agent-hints (Phase 1)."""
        spec = client.get("/openapi.json").json()

        # Handle both /inspect (Phase 1-2) and /capabilities (Phase 3+)
        inspect_path = (
            "/inspect/{id}" if "/inspect/{id}" in spec["paths"] else "/capabilities/{capability_id}"
        )
        agent_ops = [("/search", "get"), (inspect_path, "get")]

        for path, method in agent_ops:
            if path in spec["paths"] and method in spec["paths"][path]:
                op = spec["paths"][path][method]
                # Soft check (SHOULD not MUST - not all done in Phase 1)
                if "x-agent-hints" in op:
                    assert "when_to_use" in op["x-agent-hints"]
