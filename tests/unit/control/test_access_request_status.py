"""Unit tests for access-request aggregate status computation logic."""

from __future__ import annotations

import pytest

from jentic_one.control.repos.access_request_repo import compute_aggregate_status
from jentic_one.shared.models.access_requests import AccessRequestStatus


def test_all_pending_returns_pending() -> None:
    result = compute_aggregate_status(["pending", "pending", "pending"])
    assert result is AccessRequestStatus.PENDING


def test_any_pending_returns_pending() -> None:
    result = compute_aggregate_status(["approved", "pending", "denied"])
    assert result is AccessRequestStatus.PENDING


def test_all_approved_returns_approved() -> None:
    result = compute_aggregate_status(["approved", "approved", "approved"])
    assert result is AccessRequestStatus.APPROVED


def test_all_denied_returns_denied() -> None:
    result = compute_aggregate_status(["denied", "denied", "denied"])
    assert result is AccessRequestStatus.DENIED


def test_mixed_approved_and_denied_returns_partially_approved() -> None:
    result = compute_aggregate_status(["approved", "denied", "approved"])
    assert result is AccessRequestStatus.PARTIALLY_APPROVED


def test_single_approved_returns_approved() -> None:
    result = compute_aggregate_status(["approved"])
    assert result is AccessRequestStatus.APPROVED


def test_single_denied_returns_denied() -> None:
    result = compute_aggregate_status(["denied"])
    assert result is AccessRequestStatus.DENIED


def test_denied_and_withdrawn_returns_denied() -> None:
    result = compute_aggregate_status(["denied", "withdrawn"])
    assert result is AccessRequestStatus.DENIED


def test_approved_and_withdrawn_returns_partially_approved() -> None:
    result = compute_aggregate_status(["approved", "withdrawn"])
    assert result is AccessRequestStatus.PARTIALLY_APPROVED


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (["approved", "approved"], AccessRequestStatus.APPROVED),
        (["denied", "denied", "denied"], AccessRequestStatus.DENIED),
        (["approved", "denied"], AccessRequestStatus.PARTIALLY_APPROVED),
        (["pending"], AccessRequestStatus.PENDING),
        (["approved", "denied", "pending"], AccessRequestStatus.PENDING),
    ],
)
def test_parametrized_scenarios(statuses: list[str], expected: AccessRequestStatus) -> None:
    assert compute_aggregate_status(statuses) is expected
