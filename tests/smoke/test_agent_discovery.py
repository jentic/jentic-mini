"""Smoke tests for agent discovery — import, list, search, and inspect APIs."""

from __future__ import annotations

import pytest

from tests.smoke.conftest import (
    SmokeAgent,
    authed_request,
    import_and_wait,
    unique_vendor,
)


@pytest.fixture()
def agent_imported_api(base_url: str, test_agent: SmokeAgent) -> dict[str, str]:
    """Import Petstore spec as an agent and return API identity fields."""
    vendor = unique_vendor("agent-disc")
    job_body = import_and_wait(base_url, test_agent.access_token, vendor=vendor)
    job_id = job_body["job_id"]

    result_body, result_status = authed_request(
        f"{base_url}/jobs/{job_id}/result", token=test_agent.access_token
    )
    assert result_status == 200
    assert isinstance(result_body, dict)
    revisions = result_body["revisions"]
    assert len(revisions) >= 1
    api_ref = revisions[0]["api"]

    return {
        "job_id": job_id,
        "vendor": api_ref["vendor"],
        "name": api_ref["name"],
        "version": api_ref["version"],
    }


@pytest.mark.smoke
def test_agent_imports_spec(base_url: str, test_agent: SmokeAgent) -> None:
    """Agent can import a spec and the job completes successfully."""
    vendor = unique_vendor("agent-import")
    job_body = import_and_wait(base_url, test_agent.access_token, vendor=vendor)
    assert job_body["status"] == "completed"


@pytest.mark.smoke
def test_agent_lists_apis(
    base_url: str, test_agent: SmokeAgent, agent_imported_api: dict[str, str]
) -> None:
    """GET /apis with agent token shows the imported API."""
    body, status = authed_request(
        f"{base_url}/apis?vendor={agent_imported_api['vendor']}",
        token=test_agent.access_token,
    )
    assert status == 200
    assert isinstance(body, dict)
    apis = body["data"]
    matches = [
        a
        for a in apis
        if a["api"]["vendor"] == agent_imported_api["vendor"]
        and a["api"]["name"] == agent_imported_api["name"]
    ]
    assert len(matches) >= 1


@pytest.mark.smoke
def test_agent_searches_operations(base_url: str, test_agent: SmokeAgent) -> None:
    """POST /search with agent token returns results or skips if unavailable."""
    body, status = authed_request(
        f"{base_url}/search",
        method="POST",
        token=test_agent.access_token,
        body={"query": "pet"},
    )
    if status == 501:
        pytest.skip("Vector search not available in this deployment")
    assert status == 200
    assert isinstance(body, dict)


@pytest.mark.smoke
def test_agent_gets_api_by_identity(
    base_url: str, test_agent: SmokeAgent, agent_imported_api: dict[str, str]
) -> None:
    """GET /apis/{vendor}/{name}/{version} returns the API with revision_count."""
    vendor = agent_imported_api["vendor"]
    name = agent_imported_api["name"]
    version = agent_imported_api["version"]
    body, status = authed_request(
        f"{base_url}/apis/{vendor}/{name}/{version}",
        token=test_agent.access_token,
    )
    assert status == 200
    assert isinstance(body, dict)
    assert body["revision_count"] >= 1


@pytest.mark.smoke
def test_agent_lists_revisions(
    base_url: str, test_agent: SmokeAgent, agent_imported_api: dict[str, str]
) -> None:
    """GET /apis/{vendor}/{name}/{version}/revisions returns at least one revision."""
    vendor = agent_imported_api["vendor"]
    name = agent_imported_api["name"]
    version = agent_imported_api["version"]
    body, status = authed_request(
        f"{base_url}/apis/{vendor}/{name}/{version}/revisions",
        token=test_agent.access_token,
    )
    assert status == 200
    assert isinstance(body, dict)
    revisions = body["data"]
    assert len(revisions) >= 1
