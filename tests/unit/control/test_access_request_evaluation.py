"""Unit tests for access-request evaluation enforcement logic."""

from __future__ import annotations

from unittest.mock import MagicMock

from jentic_one.control.services.access_requests import NotAReviewerError
from jentic_one.control.services.access_requests import service as service_module
from jentic_one.control.services.access_requests.service import AccessRequestService
from jentic_one.shared.auth.identity import Identity


def _identity(
    sub: str = "reviewer_1",
    permissions: list[str] | None = None,
    parent_actor_id: str | None = None,
) -> Identity:
    return Identity(
        sub=sub,
        email="test@example.com",
        permissions=permissions or [],
        parent_actor_id=parent_actor_id,
    )


def _mock_request(created_by: str = "filer_1", filer_owner_id: str | None = "owner_1") -> MagicMock:
    request = MagicMock()
    request.created_by = created_by
    request.filer_owner_id = filer_owner_id
    return request


def _service() -> AccessRequestService:
    ctx = MagicMock()
    return AccessRequestService(ctx)


def test_reviewer_can_fulfill() -> None:
    svc = _service()
    identity = _identity(sub="owner_1", permissions=["agents:write"])
    request = _mock_request(created_by="filer_1", filer_owner_id="owner_1")

    result = svc._compute_evaluation(request, identity)

    assert result.can_fulfill is True
    assert all(c.passed for c in result.checks)


def test_filer_cannot_approve_own_request() -> None:
    svc = _service()
    identity = _identity(sub="filer_1", permissions=["agents:write"])
    request = _mock_request(created_by="filer_1", filer_owner_id="filer_1")

    result = svc._compute_evaluation(request, identity)

    assert result.can_fulfill is False
    not_filer_check = next(c for c in result.checks if c.check == "not_filer")
    assert not_filer_check.passed is False
    assert not_filer_check.blocker == "Cannot approve own request"


def test_missing_agents_write_blocks() -> None:
    svc = _service()
    identity = _identity(sub="owner_1", permissions=["other:scope"])
    request = _mock_request(created_by="filer_1", filer_owner_id="owner_1")

    result = svc._compute_evaluation(request, identity)

    assert result.can_fulfill is False
    scope_check = next(c for c in result.checks if c.check == "agents_write_scope")
    assert scope_check.passed is False


def test_non_owner_cannot_fulfill() -> None:
    svc = _service()
    identity = _identity(sub="other_user", permissions=["agents:write"])
    request = _mock_request(created_by="filer_1", filer_owner_id="owner_1")

    result = svc._compute_evaluation(request, identity)

    assert result.can_fulfill is False
    owns_check = next(c for c in result.checks if c.check == "owns_filer")
    assert owns_check.passed is False


def test_org_admin_satisfies_agents_write() -> None:
    svc = _service()
    identity = _identity(sub="owner_1", permissions=["org:admin"])
    request = _mock_request(created_by="filer_1", filer_owner_id="owner_1")

    result = svc._compute_evaluation(request, identity)

    assert result.can_fulfill is True


def test_admin_bypasses_owns_filer_for_unowned_agent() -> None:
    svc = _service()
    identity = _identity(sub="usr_admin", permissions=["org:admin"])
    request = _mock_request(created_by="filer_1", filer_owner_id=None)

    result = svc._compute_evaluation(request, identity)

    assert result.can_fulfill is True
    owns_check = next(c for c in result.checks if c.check == "owns_filer")
    assert owns_check.passed is True


def test_admin_bypasses_owns_filer_for_other_owner() -> None:
    svc = _service()
    identity = _identity(sub="usr_admin", permissions=["org:admin"])
    request = _mock_request(created_by="filer_1", filer_owner_id="usr_other")

    result = svc._compute_evaluation(request, identity)

    assert result.can_fulfill is True
    owns_check = next(c for c in result.checks if c.check == "owns_filer")
    assert owns_check.passed is True


def test_not_a_reviewer_error_importable() -> None:
    err = NotAReviewerError("req_123")
    assert "req_123" in str(err)


def test_not_a_reviewer_error_used_in_service() -> None:
    assert hasattr(service_module, "NotAReviewerError")
