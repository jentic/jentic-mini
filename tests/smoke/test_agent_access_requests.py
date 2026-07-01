"""Smoke tests for the access request flow (file, list, get, decide, withdraw)."""

from __future__ import annotations

import uuid

import pytest

from tests.smoke.conftest import SmokeAgent, authed_request, unique_vendor


def _create_credential_for_access(base_url: str, token: str) -> str:
    """Helper: create a credential and return its ID for access request tests."""
    vendor = unique_vendor("ar")
    body, status = authed_request(
        f"{base_url}/credentials",
        method="POST",
        token=token,
        body={
            "type": "bearer_token",
            "name": f"ar-cred-{uuid.uuid4().hex[:8]}",
            "api": {"vendor": vendor, "name": "petstore", "version": "3.0.0"},
            "provider": "static",
            "token": "sk-access-request-test",
        },
    )
    assert status == 201
    assert isinstance(body, dict)
    credential_id: str = body["credential"]["credential_id"]
    return credential_id


@pytest.mark.smoke
def test_file_access_request(base_url: str, test_agent: SmokeAgent) -> None:
    """POST /access-requests creates a pending request."""
    credential_id = _create_credential_for_access(base_url, test_agent.owner_token)

    body, status = authed_request(
        f"{base_url}/access-requests",
        method="POST",
        token=test_agent.access_token,
        body={
            "reason": "Smoke test access request",
            "items": [
                {
                    "resource_type": "credential",
                    "action": "read",
                    "resource_id": credential_id,
                }
            ],
        },
    )
    assert status == 202
    assert isinstance(body, dict)
    assert "request_id" in body
    assert body["status"] == "pending"


@pytest.mark.smoke
def test_list_access_requests(base_url: str, test_agent: SmokeAgent) -> None:
    """GET /access-requests lists the filed request."""
    credential_id = _create_credential_for_access(base_url, test_agent.owner_token)

    file_body, _ = authed_request(
        f"{base_url}/access-requests",
        method="POST",
        token=test_agent.access_token,
        body={
            "reason": "List test",
            "items": [
                {
                    "resource_type": "credential",
                    "action": "read",
                    "resource_id": credential_id,
                }
            ],
        },
    )
    assert isinstance(file_body, dict)
    request_id = file_body["request_id"]

    body, status = authed_request(
        f"{base_url}/access-requests",
        token=test_agent.access_token,
    )
    assert status == 200
    assert isinstance(body, dict)
    request_ids = [r["request_id"] for r in body["data"]]
    assert request_id in request_ids


@pytest.mark.smoke
def test_get_access_request(base_url: str, test_agent: SmokeAgent) -> None:
    """GET /access-requests/{id} returns the request with items."""
    credential_id = _create_credential_for_access(base_url, test_agent.owner_token)

    file_body, _ = authed_request(
        f"{base_url}/access-requests",
        method="POST",
        token=test_agent.access_token,
        body={
            "reason": "Get test",
            "items": [
                {
                    "resource_type": "credential",
                    "action": "read",
                    "resource_id": credential_id,
                }
            ],
        },
    )
    assert isinstance(file_body, dict)
    request_id = file_body["request_id"]

    body, status = authed_request(
        f"{base_url}/access-requests/{request_id}",
        token=test_agent.access_token,
    )
    assert status == 200
    assert isinstance(body, dict)
    assert body["request_id"] == request_id
    assert "items" in body
    assert len(body["items"]) >= 1


@pytest.mark.smoke
def test_decide_access_request_approve(base_url: str, test_agent: SmokeAgent) -> None:
    """POST /access-requests/{id}:decide approves the request."""
    credential_id = _create_credential_for_access(base_url, test_agent.owner_token)

    file_body, _ = authed_request(
        f"{base_url}/access-requests",
        method="POST",
        token=test_agent.access_token,
        body={
            "reason": "Decide test",
            "items": [
                {
                    "resource_type": "credential",
                    "action": "read",
                    "resource_id": credential_id,
                }
            ],
        },
    )
    assert isinstance(file_body, dict)
    request_id = file_body["request_id"]

    # Get the item_id from the request details
    detail_body, _ = authed_request(
        f"{base_url}/access-requests/{request_id}",
        token=test_agent.owner_token,
    )
    assert isinstance(detail_body, dict)
    item_id = detail_body["items"][0]["item_id"]

    # Approve via admin/owner
    decide_body, decide_status = authed_request(
        f"{base_url}/access-requests/{request_id}:decide",
        method="POST",
        token=test_agent.owner_token,
        body={
            "items": [
                {
                    "item_id": item_id,
                    "decision": "approved",
                    "decision_reason": "Smoke test approval",
                }
            ],
        },
    )
    assert decide_status == 200
    assert isinstance(decide_body, dict)
    assert decide_body["status"] == "approved"


@pytest.mark.smoke
def test_withdraw_access_request(base_url: str, test_agent: SmokeAgent) -> None:
    """POST /access-requests/{id}:withdraw moves to withdrawn."""
    credential_id = _create_credential_for_access(base_url, test_agent.owner_token)

    file_body, _ = authed_request(
        f"{base_url}/access-requests",
        method="POST",
        token=test_agent.access_token,
        body={
            "reason": "Withdraw test",
            "items": [
                {
                    "resource_type": "credential",
                    "action": "read",
                    "resource_id": credential_id,
                }
            ],
        },
    )
    assert isinstance(file_body, dict)
    request_id = file_body["request_id"]

    body, status = authed_request(
        f"{base_url}/access-requests/{request_id}:withdraw",
        method="POST",
        token=test_agent.access_token,
    )
    assert status == 200
    assert isinstance(body, dict)
    assert body["status"] == "withdrawn"
