"""Unit tests for AuditRepository._compute_diff logic."""

from __future__ import annotations

from jentic_one.admin.repos.audit_repo import AuditRepository


def test_compute_diff_both_none_returns_none() -> None:
    assert AuditRepository._compute_diff(None, None) is None


def test_compute_diff_create_returns_all_keys_as_added() -> None:
    after = {"name": "Alice", "role": "admin"}
    result = AuditRepository._compute_diff(None, after)
    assert result == {"added": {"name": "Alice", "role": "admin"}}


def test_compute_diff_delete_returns_all_keys_as_removed() -> None:
    before = {"name": "Alice", "role": "admin"}
    result = AuditRepository._compute_diff(before, None)
    assert result == {"removed": {"name": "Alice", "role": "admin"}}


def test_compute_diff_update_with_changed_added_and_removed_keys() -> None:
    before = {"name": "Alice", "role": "admin", "active": True}
    after = {"name": "Bob", "role": "admin", "email": "bob@example.com"}
    result = AuditRepository._compute_diff(before, after)
    assert result == {
        "modified": {"name": {"old": "Alice", "new": "Bob"}},
        "removed": {"active": True},
        "added": {"email": "bob@example.com"},
    }


def test_compute_diff_no_changes_returns_none() -> None:
    data = {"name": "Alice", "role": "admin"}
    result = AuditRepository._compute_diff(data, data.copy())
    assert result is None
