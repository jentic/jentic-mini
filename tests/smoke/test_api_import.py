"""Smoke tests for API spec import, job polling, and registry queries."""

from __future__ import annotations

import pytest

from tests.smoke.conftest import (
    SmokeUser,
    authed_request,
    import_and_wait,
    petstore_import_source,
    unique_vendor,
)


@pytest.fixture()
def imported_api(base_url: str, test_user: SmokeUser) -> dict[str, str]:
    """Import the Petstore spec and poll until the job completes.

    Returns a dict with keys: job_id, vendor, name, version.
    """
    job_body = import_and_wait(base_url, test_user.token)
    job_id = job_body["job_id"]

    result_body, result_status = authed_request(
        f"{base_url}/jobs/{job_id}/result", token=test_user.token
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
def test_import_spec_from_url(base_url: str, test_user: SmokeUser) -> None:
    """Submitting a URL-based import returns 202 with a queued job."""
    body, status = authed_request(
        f"{base_url}/apis",
        method="POST",
        token=test_user.token,
        body={"sources": [petstore_import_source(vendor=unique_vendor())]},
    )
    assert status == 202
    assert isinstance(body, dict)
    assert "job_id" in body
    assert body["status"] == "queued"


@pytest.mark.smoke
def test_poll_import_job(base_url: str, imported_api: dict[str, str], test_user: SmokeUser) -> None:
    """A completed import job has status 'completed'."""
    body, status = authed_request(
        f"{base_url}/jobs/{imported_api['job_id']}", token=test_user.token
    )
    assert status == 200
    assert isinstance(body, dict)
    assert body["status"] == "completed"


@pytest.mark.smoke
def test_list_apis_after_import(
    base_url: str, imported_api: dict[str, str], test_user: SmokeUser
) -> None:
    """After import, the API appears in the list."""
    body, status = authed_request(
        f"{base_url}/apis?vendor={imported_api['vendor']}", token=test_user.token
    )
    assert status == 200
    assert isinstance(body, dict)
    apis = body["data"]
    matches = [
        a
        for a in apis
        if a["api"]["vendor"] == imported_api["vendor"] and a["api"]["name"] == imported_api["name"]
    ]
    assert len(matches) >= 1


@pytest.mark.smoke
def test_get_api_by_identity(
    base_url: str, imported_api: dict[str, str], test_user: SmokeUser
) -> None:
    """Fetch a specific API by vendor/name/version."""
    vendor = imported_api["vendor"]
    name = imported_api["name"]
    version = imported_api["version"]
    body, status = authed_request(
        f"{base_url}/apis/{vendor}/{name}/{version}", token=test_user.token
    )
    assert status == 200
    assert isinstance(body, dict)
    assert body["revision_count"] >= 1


@pytest.mark.smoke
def test_list_revisions(base_url: str, imported_api: dict[str, str], test_user: SmokeUser) -> None:
    """Imported API has at least one revision with source.type == 'url'."""
    vendor = imported_api["vendor"]
    name = imported_api["name"]
    version = imported_api["version"]
    body, status = authed_request(
        f"{base_url}/apis/{vendor}/{name}/{version}/revisions", token=test_user.token
    )
    assert status == 200
    assert isinstance(body, dict)
    revisions = body["data"]
    assert len(revisions) >= 1
    rev = revisions[0]
    assert rev["state"] in ("draft", "current")
    assert rev["source"]["type"] == "url"


@pytest.mark.smoke
def test_get_single_revision(
    base_url: str, imported_api: dict[str, str], test_user: SmokeUser
) -> None:
    """Fetch a single revision by ID and verify its fields."""
    vendor = imported_api["vendor"]
    name = imported_api["name"]
    version = imported_api["version"]

    list_body, _ = authed_request(
        f"{base_url}/apis/{vendor}/{name}/{version}/revisions", token=test_user.token
    )
    assert isinstance(list_body, dict)
    revision_id = list_body["data"][0]["revision_id"]

    body, status = authed_request(
        f"{base_url}/apis/{vendor}/{name}/{version}/revisions/{revision_id}",
        token=test_user.token,
    )
    assert status == 200
    assert isinstance(body, dict)
    assert body["revision_id"] == revision_id
    assert body["operation_count"] > 0
