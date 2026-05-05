"""HTML rendering regression tests.

Two endpoints render HTML inline with `html.escape()` — formerly via an
`import html as _html` alias, now via plain `import html`. Reassigning a
local variable named `html` in the same function would shadow the module
and raise UnboundLocalError on the first `html.escape()` call.

These tests exercise the HTML branches at the HTTP boundary to lock in
the scoping behaviour.

  - GET /toolkits/{id}/access-requests/approve/{req_id}/legacy
  - GET /workflows/{slug} with Accept: text/html
    (exercised against an isolated test app because the real app's SPA
    middleware intercepts any request with text/html in Accept on
    /workflows/* — see jentic/jentic-mini#255.)
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from src.routers import workflows as workflows_router
from starlette.testclient import TestClient


# ── Workflow HTML rendering ───────────────────────────────────────────────────


@pytest.fixture(scope="module")
def workflows_only_client(client):
    """TestClient against a minimal app mounting only the workflows router.

    The real app's SPA middleware intercepts GET requests with text/html in
    Accept on /workflows/* and returns the React SPA instead of reaching the
    route. A minimal app omits that middleware so the HTML branch is
    reachable. The shared DB_PATH is still used (set by conftest), so the
    workflow imported by the `imported_html_workflow` fixture via the main
    client is visible here.

    Depends on `client` to ensure the main app's lifespan (and therefore
    run_migrations()) has executed before we query the DB.
    """
    mini_app = FastAPI()
    mini_app.include_router(workflows_router.router)
    with TestClient(mini_app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def imported_html_workflow(admin_client):
    """Import a workflow once for the module via the real app."""
    workflow_path = Path(__file__).parent / "fixtures" / "test-workflow.arazzo.json"
    assert workflow_path.exists(), f"Test workflow fixture not found: {workflow_path}"

    resp = admin_client.post(
        "/import",
        json={"sources": [{"type": "path", "path": str(workflow_path)}]},
    )
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    result = resp.json()
    assert result["succeeded"] > 0


def test_get_workflow_html_renders(workflows_only_client, imported_html_workflow):
    """GET /workflows/{slug} with Accept: text/html returns rendered HTML.

    Proves html.escape() in the HTML branch works without UnboundLocalError.
    """
    resp = workflows_only_client.get(
        "/workflows/test-workflow",
        headers={"Accept": "text/html"},
    )
    assert resp.status_code == 200, f"HTML workflow page failed: {resp.text}"
    body = resp.text
    # Escaped workflow name must be present — proves html.escape was called
    assert "Test Workflow" in body
    # Steps block must be rendered — proves the esc(...) loop completed
    assert "<h2>Steps (2)</h2>" in body
    assert "searchItems" in body or "getItem" in body
    # Must be HTML content type
    assert "text/html" in resp.headers["content-type"]


# ── Access request legacy approval UI ─────────────────────────────────────────


@pytest.fixture
def access_request(client, agent_key_header):
    """Create an access request and return (toolkit_id, req_id)."""
    toolkit_id = "default"
    resp = client.post(
        f"/toolkits/{toolkit_id}/access-requests",
        headers=agent_key_header,
        json={
            "type": "grant",
            "credential_id": "some-credential",
            "rules": [{"effect": "allow", "methods": ["GET"]}],
            "reason": "Need read access <script>alert(1)</script>",
        },
    )
    assert resp.status_code in (200, 201, 202), f"Create request failed: {resp.text}"
    return toolkit_id, resp.json()["id"]


def test_approval_ui_legacy_pending_renders(admin_client, access_request):
    """Legacy HTML approval UI renders for a pending request."""
    toolkit_id, req_id = access_request
    resp = admin_client.get(
        f"/toolkits/{toolkit_id}/access-requests/approve/{req_id}/legacy",
    )
    assert resp.status_code == 200, f"Legacy UI failed: {resp.text}"
    body = resp.text
    # Request metadata escaped into the page
    assert req_id in body
    assert "grant" in body
    # Reason is escaped — `<script>` must not appear literally
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    # Pending branch: Approve/Deny buttons present
    assert "Approve" in body
    assert "Deny" in body
    assert "text/html" in resp.headers["content-type"]


def test_approval_ui_legacy_resolved_renders(admin_client, access_request):
    """Legacy HTML approval UI renders the resolved branch after denial."""
    toolkit_id, req_id = access_request
    # Deny to leave the request in a non-pending state without side effects
    resp = admin_client.post(
        f"/toolkits/{toolkit_id}/access-requests/{req_id}/deny",
    )
    assert resp.status_code in (200, 201), f"Deny failed: {resp.text}"

    resp = admin_client.get(
        f"/toolkits/{toolkit_id}/access-requests/approve/{req_id}/legacy",
    )
    assert resp.status_code == 200, f"Legacy UI (resolved) failed: {resp.text}"
    body = resp.text
    # Resolved branch: no Approve/Deny buttons, just the "already resolved" line
    assert "already been resolved" in body
    assert "denied" in body


def test_approval_ui_legacy_not_found(admin_client):
    """Legacy HTML approval UI returns 404 HTML for unknown req_id."""
    resp = admin_client.get(
        "/toolkits/default/access-requests/approve/areq_missing/legacy",
    )
    assert resp.status_code == 404
    assert "Not found" in resp.text
