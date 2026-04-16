"""Self-hosted API import tests — auto-overlay generation behavior.

When importing a spec with a hardcoded private server URL (e.g. http://localhost:8123),
the import should auto-generate an overlay that replaces it with http://{host}.

When the spec already has template variables (e.g. http://{defaultHost}), the import
should NOT overwrite them with a different variable name.
"""
import json


def test_auto_overlay_for_hardcoded_localhost(client, admin_session):
    """Importing a spec with hardcoded localhost should auto-generate a {host} overlay."""
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Home Assistant", "version": "1.0"},
        "servers": [{"url": "http://localhost:8123"}],
        "paths": {"/api": {"get": {"operationId": "test", "responses": {"200": {"description": "ok"}}}}},
    }
    resp = client.post("/import", cookies=admin_session, json={
        "sources": [{"type": "inline", "content": json.dumps(spec), "filename": "ha.json"}],
    })
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    result = resp.json()["results"][0]
    assert result.get("self_hosted") is True
    assert result.get("overlay_generated") is True


def test_no_auto_overlay_for_template_url(client, admin_session):
    """Importing a spec with existing template variables should NOT auto-generate an overlay.

    Regression: previously the auto-overlay unconditionally replaced any template
    variable (e.g. {defaultHost}) with {host}, breaking specs that already had
    their own variable names.
    """
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Discourse", "version": "1.0"},
        "servers": [{"url": "https://{defaultHost}", "variables": {
            "defaultHost": {"default": "localhost:3000", "description": "Discourse instance"}
        }}],
        "paths": {"/posts": {"get": {"operationId": "listPosts", "responses": {"200": {"description": "ok"}}}}},
    }
    resp = client.post("/import", cookies=admin_session, json={
        "sources": [{"type": "inline", "content": json.dumps(spec), "filename": "discourse.json"}],
    })
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    result = resp.json()["results"][0]
    assert result.get("self_hosted") is True
    assert result.get("overlay_generated") is not True, (
        "Should NOT generate auto-overlay when spec already has template variables"
    )
