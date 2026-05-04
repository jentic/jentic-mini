"""Tests for workflow import and loading functionality.

Ensures that both local and catalog workflows can be successfully imported
and loaded without errors (regression test for pathlib.Path shadowing issue).
"""

import json
from pathlib import Path

import pytest
from src.config import JENTIC_PUBLIC_HOSTNAME


@pytest.fixture(scope="module")
def imported_workflow(admin_client):
    """Import the test workflow fixture once for the module."""
    workflow_path = Path(__file__).parent / "fixtures" / "test-workflow.arazzo.json"
    assert workflow_path.exists(), f"Test workflow fixture not found: {workflow_path}"

    resp = admin_client.post(
        "/import",
        json={"sources": [{"type": "path", "path": str(workflow_path)}]},
    )
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    result = resp.json()
    assert result["succeeded"] > 0, "Expected at least one workflow to be imported"
    return result


def test_import_local_workflow_via_path(admin_client, imported_workflow):
    """Import a local workflow file and verify it appears in the list."""
    assert imported_workflow["status"] == "ok"

    resp = admin_client.get("/workflows")
    assert resp.status_code == 200, f"List workflows failed: {resp.text}"
    workflows = resp.json()
    assert isinstance(workflows, list)
    assert len(workflows) > 0, "Expected at least one workflow after import"

    test_workflow = next((w for w in workflows if w.get("slug") == "test-workflow"), None)
    assert test_workflow is not None, "Test workflow not found in list"
    assert "test workflow" in test_workflow["name"].lower()
    assert test_workflow["source"] == "local"
    assert test_workflow["steps_count"] == 2


def test_load_workflow_detail(admin_client, imported_workflow):
    """Load workflow detail endpoint — should not error with pathlib.Path shadowing."""
    resp = admin_client.get("/workflows/test-workflow")
    assert resp.status_code == 200, f"Load workflow detail failed: {resp.text}"

    workflow = resp.json()
    assert workflow["slug"] == "test-workflow"
    assert "test workflow" in workflow["name"].lower()
    assert "steps" in workflow
    assert len(workflow["steps"]) == 2


def test_inspect_workflow_capability(admin_client, imported_workflow):
    """Load workflow via inspect endpoint — tests capability.py pathlib usage."""
    capability_id = f"POST/{JENTIC_PUBLIC_HOSTNAME}/workflows/test-workflow"

    resp = admin_client.get(f"/inspect/{capability_id}")
    assert resp.status_code == 200, f"Inspect workflow failed: {resp.text}"

    capability = resp.json()
    assert capability["id"] == capability_id
    assert capability["type"] == "workflow"
    assert "test workflow" in capability["name"].lower()


def test_import_inline_workflow(admin_client):
    """Import a workflow via inline content (tests inline import path)."""
    workflow_content = {
        "arazzo": "1.0.0",
        "info": {"title": "Inline Test Workflow", "version": "1.0.0"},
        "workflows": [
            {
                "workflowId": "inline-test",
                "summary": "Inline workflow",
                "steps": [
                    {"stepId": "step1", "description": "First step", "operationId": "test.op1"}
                ],
            }
        ],
    }

    resp = admin_client.post(
        "/import",
        json={
            "sources": [
                {
                    "type": "inline",
                    "content": json.dumps(workflow_content),
                    "filename": "inline-test.arazzo.json",
                }
            ]
        },
    )
    assert resp.status_code == 200, f"Import inline workflow failed: {resp.text}"
    result = resp.json()
    assert result["succeeded"] > 0

    resp = admin_client.get("/workflows/inline-test")
    assert resp.status_code == 200, f"Load inline workflow failed: {resp.text}"
    workflow = resp.json()
    assert workflow["slug"] == "inline-test"
    assert "inline workflow" in workflow["name"].lower()
