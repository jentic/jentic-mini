"""Integration tests for AuditEntry model and AuditRepository."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from jentic_one.admin.core.schema.audit import AuditEntry
from jentic_one.admin.repos import AuditRepository
from jentic_one.shared.db.session import DatabaseSession
from jentic_one.shared.models import AuditAction, AuditTargetType

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_audit(admin_db: DatabaseSession) -> AsyncGenerator[None, None]:
    """Ensure the ``audit_entries`` table is empty before and after each test."""
    async with admin_db.session() as session:
        await session.execute(delete(AuditEntry))
        await session.commit()
    yield
    async with admin_db.session() as session:
        await session.execute(delete(AuditEntry))
        await session.commit()


async def test_record_round_trip(admin_db: DatabaseSession, clean_audit: None) -> None:
    """record() persists an entry that get_by_id() can retrieve with all fields."""
    async with admin_db.session() as session:
        entry = await AuditRepository.record(
            session,
            action=AuditAction.PROMOTE,
            target_type=AuditTargetType.REVISION,
            target_id="rev-123",
            actor_type="user",
            actor_id="user-42",
            actor_session_id="sess-abc",
            target_parent_id="parent-1",
            request_id="req-xyz",
            trace_id="trace-001",
            job_id="job_test12345678901234",
            reason="Approved by lead",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
        )
        await session.commit()
        entry_id = entry.id

    async with admin_db.session() as session:
        loaded = await AuditRepository.get_by_id(session, entry_id)
        assert loaded is not None
        assert loaded.action == AuditAction.PROMOTE
        assert loaded.target_type == AuditTargetType.REVISION
        assert loaded.target_id == "rev-123"
        assert loaded.actor_type == "user"
        assert loaded.actor_id == "user-42"
        assert loaded.actor_session_id == "sess-abc"
        assert loaded.target_parent_id == "parent-1"
        assert loaded.request_id == "req-xyz"
        assert loaded.trace_id == "trace-001"
        assert loaded.job_id == "job_test12345678901234"
        assert loaded.reason == "Approved by lead"
        assert loaded.ip_address == "192.168.1.1"
        assert loaded.user_agent == "TestAgent/1.0"
        assert loaded.occurred_at is not None


async def test_record_with_diff_computation(admin_db: DatabaseSession, clean_audit: None) -> None:
    """record() auto-populates diff when before and after are provided."""
    async with admin_db.session() as session:
        entry = await AuditRepository.record(
            session,
            action=AuditAction.UPDATE,
            target_type=AuditTargetType.PERMISSION,
            target_id="perm-1",
            actor_type="user",
            before={"level": "read", "scope": "org"},
            after={"level": "write", "scope": "org"},
        )
        await session.commit()
        entry_id = entry.id

    async with admin_db.session() as session:
        loaded = await AuditRepository.get_by_id(session, entry_id)
        assert loaded is not None
        assert loaded.diff == {"modified": {"level": {"old": "read", "new": "write"}}}
        assert loaded.before == {"level": "read", "scope": "org"}
        assert loaded.after == {"level": "write", "scope": "org"}


async def test_list_by_target(admin_db: DatabaseSession, clean_audit: None) -> None:
    """list_by_target() returns filtered entries in DESC order."""
    actions = [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.DELETE]
    async with admin_db.session() as session:
        for action in actions:
            await AuditRepository.record(
                session,
                action=action,
                target_type=AuditTargetType.REVISION,
                target_id="rev-A",
                actor_type="user",
            )
        await AuditRepository.record(
            session,
            action=AuditAction.CREATE,
            target_type=AuditTargetType.REVISION,
            target_id="rev-B",
            actor_type="user",
        )
        await session.commit()

    async with admin_db.session() as session:
        entries = await AuditRepository.list_by_target(session, AuditTargetType.REVISION, "rev-A")
        assert len(entries) == 3
        assert all(e.target_id == "rev-A" for e in entries)
        for i in range(len(entries) - 1):
            assert entries[i].occurred_at >= entries[i + 1].occurred_at


async def test_list_by_actor(admin_db: DatabaseSession, clean_audit: None) -> None:
    """list_by_actor() filters by actor_id and returns DESC order."""
    async with admin_db.session() as session:
        await AuditRepository.record(
            session,
            action=AuditAction.CREATE,
            target_type=AuditTargetType.USER,
            target_id="t1",
            actor_type="user",
            actor_id="alice",
        )
        await AuditRepository.record(
            session,
            action=AuditAction.UPDATE,
            target_type=AuditTargetType.USER,
            target_id="t2",
            actor_type="user",
            actor_id="alice",
        )
        await AuditRepository.record(
            session,
            action=AuditAction.DELETE,
            target_type=AuditTargetType.USER,
            target_id="t3",
            actor_type="user",
            actor_id="bob",
        )
        await session.commit()

    async with admin_db.session() as session:
        entries = await AuditRepository.list_by_actor(session, "alice")
        assert len(entries) == 2
        assert all(e.actor_id == "alice" for e in entries)


async def test_list_all_with_time_bounds(admin_db: DatabaseSession, clean_audit: None) -> None:
    """list_all() respects since/until time bounds."""
    now = datetime.now(tz=UTC)
    async with admin_db.session() as session:
        for i in range(5):
            entry = AuditEntry(
                action=f"action-{i}",
                target_type="t",
                target_id="t1",
                actor_type="user",
                occurred_at=now - timedelta(hours=5 - i),
            )
            session.add(entry)
        await session.commit()

    async with admin_db.session() as session:
        entries = await AuditRepository.list_all(
            session,
            since=now - timedelta(hours=3),
            until=now - timedelta(hours=1),
        )
        assert len(entries) == 3
        for e in entries:
            assert e.occurred_at >= now - timedelta(hours=3)
            assert e.occurred_at <= now - timedelta(hours=1)


async def test_append_only_invariant(admin_db: DatabaseSession, clean_audit: None) -> None:
    """AuditEntry has no updated_at column and repository exposes no update method."""
    columns = {c.name for c in AuditEntry.__table__.columns}
    assert "updated_at" not in columns
    assert not hasattr(AuditRepository, "update")
