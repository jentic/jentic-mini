"""Smoke tests for job listing and retrieval."""

from __future__ import annotations

import pytest

from tests.smoke.conftest import SmokeUser, authed_request, import_and_wait


@pytest.fixture()
def completed_job(base_url: str, test_user: SmokeUser) -> dict[str, str]:
    """Trigger an import and wait for completion. Returns dict with job_id."""
    job_body = import_and_wait(base_url, test_user.token)
    return {"job_id": job_body["job_id"]}


@pytest.mark.smoke
def test_list_jobs(base_url: str, completed_job: dict[str, str], test_user: SmokeUser) -> None:
    """After an import, the jobs list contains at least one import job."""
    body, status = authed_request(f"{base_url}/jobs?kind=import", token=test_user.token)
    assert status == 200
    assert isinstance(body, dict)
    assert "data" in body
    assert len(body["data"]) >= 1
    kinds = [j["kind"] for j in body["data"]]
    assert "import" in kinds


@pytest.mark.smoke
def test_get_job_by_id(base_url: str, completed_job: dict[str, str], test_user: SmokeUser) -> None:
    """Fetching a specific job by ID returns expected fields."""
    body, status = authed_request(
        f"{base_url}/jobs/{completed_job['job_id']}", token=test_user.token
    )
    assert status == 200
    assert isinstance(body, dict)
    assert body["job_id"] == completed_job["job_id"]
    assert "kind" in body
    assert "status" in body


@pytest.mark.smoke
def test_get_job_result(base_url: str, completed_job: dict[str, str], test_user: SmokeUser) -> None:
    """A completed import job exposes its result payload."""
    body, status = authed_request(
        f"{base_url}/jobs/{completed_job['job_id']}/result", token=test_user.token
    )
    assert status == 200
    assert isinstance(body, dict)
    assert "revisions" in body
    assert len(body["revisions"]) >= 1
