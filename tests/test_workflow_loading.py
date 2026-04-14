"""Tests for workflow import and loading functionality.

Ensures that both local and catalog workflows can be successfully imported
and loaded without errors (regression test for pathlib.Path shadowing issue).
"""
import json
import os
from pathlib import Path


def test_import_local_workflow_via_path(client, admin_session):
    """Import a local workflow file and verify it loads without errors."""
    # Path to test workflow fixture
    workflow_path = Path(__file__).parent / "fixtures" / "test-workflow.arazzo.json"
    assert workflow_path.exists(), f"Test workflow fixture not found: {workflow_path}"

    # Import the workflow via POST /import
    response = client.post(
        "/import",
        json={
            "sources": [
                {
                    "type": "path",
                    "path": str(workflow_path),
                }
            ]
        },
        cookies=admin_session,
    )
    assert response.status_code == 200, f"Import failed: {response.text}"
    result = response.json()
    assert result["succeeded"] > 0, "Expected at least one workflow to be imported"
    assert result["status"] == "ok", f"Import status not ok: {result}"

    # List workflows - should include our imported workflow
    response = client.get("/workflows", cookies=admin_session)
    assert response.status_code == 200, f"List workflows failed: {response.text}"
    workflows = response.json()
    assert isinstance(workflows, list), "Expected workflows to be a list"
    assert len(workflows) > 0, "Expected at least one workflow after import"

    # Find our test workflow
    test_workflow = next((w for w in workflows if w.get("slug") == "test-workflow"), None)
    assert test_workflow is not None, "Test workflow not found in list"
    # The name comes from workflow.summary, not info.title
    assert "test workflow" in test_workflow["name"].lower()
    assert test_workflow["source"] == "local"
    assert test_workflow["steps_count"] == 2


def test_load_workflow_detail(client, admin_session):
    """Load workflow detail endpoint - should not error with pathlib.Path shadowing."""
    # Import workflow first
    workflow_path = Path(__file__).parent / "fixtures" / "test-workflow.arazzo.json"
    import_resp = client.post(
        "/import",
        json={"sources": [{"type": "path", "path": str(workflow_path)}]},
        cookies=admin_session,
    )
    assert import_resp.status_code == 200, f"Import failed: {import_resp.text}"

    # Load workflow detail via GET /workflows/{slug}
    # Key test: should return 200, not 500 (pathlib.Path shadowing would cause 500)
    response = client.get("/workflows/test-workflow", cookies=admin_session)
    assert response.status_code == 200, f"Load workflow detail failed: {response.text}"

    workflow = response.json()
    assert workflow["slug"] == "test-workflow"
    # Name comes from workflow.summary field
    assert "test workflow" in workflow["name"].lower()
    assert "steps" in workflow
    assert len(workflow["steps"]) == 2


def test_inspect_workflow_capability(client, admin_session):
    """Load workflow via inspect endpoint - tests capability.py pathlib usage."""
    # Import workflow first
    workflow_path = Path(__file__).parent / "fixtures" / "test-workflow.arazzo.json"
    import_resp = client.post(
        "/import",
        json={"sources": [{"type": "path", "path": str(workflow_path)}]},
        cookies=admin_session,
    )
    assert import_resp.status_code == 200, f"Import failed: {import_resp.text}"

    # Inspect via capability ID format: POST/{host}/workflows/{slug}
    from src.config import JENTIC_PUBLIC_HOSTNAME
    capability_id = f"POST/{JENTIC_PUBLIC_HOSTNAME}/workflows/test-workflow"

    # Key test: should return 200, not 500 (pathlib.Path shadowing would cause 500)
    response = client.get(f"/inspect/{capability_id}", cookies=admin_session)
    assert response.status_code == 200, f"Inspect workflow failed: {response.text}"

    capability = response.json()
    # Basic validation - exact schema may vary but should have workflow info
    assert capability["id"] == capability_id
    assert capability["type"] == "workflow"
    assert "test workflow" in capability["name"].lower()


def test_import_inline_workflow(client, admin_session):
    """Import a workflow via inline content (tests inline import path)."""
    workflow_content = {
        "arazzo": "1.0.0",
        "info": {
            "title": "Inline Test Workflow",
            "version": "1.0.0"
        },
        "workflows": [
            {
                "workflowId": "inline-test",
                "summary": "Inline workflow",
                "steps": [
                    {
                        "stepId": "step1",
                        "description": "First step",
                        "operationId": "test.op1"
                    }
                ]
            }
        ]
    }

    response = client.post(
        "/import",
        json={
            "sources": [
                {
                    "type": "inline",
                    "content": json.dumps(workflow_content),
                    "filename": "inline-test.arazzo.json"
                }
            ]
        },
        cookies=admin_session,
    )
    assert response.status_code == 200, f"Import inline workflow failed: {response.text}"
    result = response.json()
    assert result["succeeded"] > 0, f"Expected at least one workflow to be imported, got: {result}"

    # Verify it's loadable
    response = client.get("/workflows/inline-test", cookies=admin_session)
    assert response.status_code == 200, f"Load inline workflow failed: {response.text}"
    workflow = response.json()
    assert workflow["slug"] == "inline-test"
    assert "inline workflow" in workflow["name"].lower()
