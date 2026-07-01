"""Integration tests for the shared audit recording helpers.

Exercises :func:`record_audit` (atomic) and :func:`record_audit_best_effort`
(separate transaction, never raises) against a real database — no mocking.

The key guarantee for the best-effort variant is that an audit failure is
swallowed: a caller whose primary mutation has already committed against a
non-admin database must never have that mutation broken by an audit error.
"""

from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from jentic_one.admin.core.schema.audit import AuditEntry
from jentic_one.shared.audit import record_audit, record_audit_best_effort
from jentic_one.shared.context import Context
from jentic_one.shared.models.audit import AuditAction, AuditTargetType

pytestmark = pytest.mark.integration


async def _entries_for(ctx: Context, target_id: str) -> list[AuditEntry]:
    async with ctx.admin_db.session() as session:
        result = await session.execute(
            select(AuditEntry)
            .where(AuditEntry.target_id == target_id)
            .order_by(AuditEntry.occurred_at.desc())
        )
        return list(result.scalars().all())


async def _cleanup(ctx: Context, target_id: str) -> None:
    async with ctx.admin_db.session() as session:
        await session.execute(delete(AuditEntry).where(AuditEntry.target_id == target_id))
        await session.commit()


async def test_record_audit_persists_inside_caller_transaction(
    integration_context: Context,
) -> None:
    ctx = integration_context
    target_id = "test-record-audit-atomic"
    try:
        async with ctx.admin_db.transaction() as session:
            await record_audit(
                session,
                action=AuditAction.CREATE,
                target_type=AuditTargetType.USER,
                target_id=target_id,
                actor_type="user",
                actor_id="actor-atomic",
            )

        entries = await _entries_for(ctx, target_id)
        assert len(entries) == 1
        assert entries[0].action == AuditAction.CREATE.value
        assert entries[0].actor_id == "actor-atomic"
    finally:
        await _cleanup(ctx, target_id)


async def test_record_audit_rolls_back_with_caller_transaction(
    integration_context: Context,
) -> None:
    ctx = integration_context
    target_id = "test-record-audit-rollback"
    try:
        with pytest.raises(RuntimeError):
            async with ctx.admin_db.transaction() as session:
                await record_audit(
                    session,
                    action=AuditAction.CREATE,
                    target_type=AuditTargetType.USER,
                    target_id=target_id,
                    actor_type="user",
                    actor_id="actor-rollback",
                )
                raise RuntimeError("force rollback")

        # The audit entry must have rolled back with the caller's transaction.
        entries = await _entries_for(ctx, target_id)
        assert entries == []
    finally:
        await _cleanup(ctx, target_id)


async def test_record_audit_best_effort_persists_in_separate_transaction(
    integration_context: Context,
) -> None:
    ctx = integration_context
    target_id = "test-best-effort-persist"
    try:
        await record_audit_best_effort(
            ctx,
            action=AuditAction.UPDATE,
            target_type=AuditTargetType.NOTE,
            target_id=target_id,
            actor_type="user",
        )

        entries = await _entries_for(ctx, target_id)
        assert len(entries) == 1
        assert entries[0].action == AuditAction.UPDATE.value
        assert entries[0].target_type == AuditTargetType.NOTE.value
        assert entries[0].actor_type == "user"
    finally:
        await _cleanup(ctx, target_id)


async def test_record_audit_best_effort_swallows_failures(
    integration_context: Context,
) -> None:
    """A bad payload must not raise — the primary mutation already committed."""
    ctx = integration_context
    target_id = "test-best-effort-swallow"
    try:
        # ``target_id=None`` violates the NOT NULL constraint, forcing the
        # flush inside record_audit to fail. The helper must swallow it.
        await record_audit_best_effort(
            ctx,
            action=AuditAction.DELETE,
            target_type=AuditTargetType.NOTE,
            target_id=None,  # type: ignore[arg-type]
            actor_type="user",
        )

        # Nothing should have been persisted and no exception propagated.
        entries = await _entries_for(ctx, target_id)
        assert entries == []
    finally:
        await _cleanup(ctx, target_id)
