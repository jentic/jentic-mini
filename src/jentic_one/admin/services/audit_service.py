"""Read-only audit log query service."""

from __future__ import annotations

from jentic_one.admin.core.schema.audit import AuditEntry
from jentic_one.admin.repos import AuditRepository
from jentic_one.admin.services._support.pagination import Page, decode_cursor, encode_cursor
from jentic_one.admin.services.errors import AuditEntryNotFoundError, InvalidInputError
from jentic_one.admin.services.schemas.audit import AuditFilter, AuditView
from jentic_one.shared.context import Context


class AuditService:
    """Provides read-only access to the audit log."""

    def __init__(self, ctx: Context) -> None:
        self._ctx = ctx

    async def list_all(
        self,
        filter: AuditFilter,
        cursor: str | None = None,
        limit: int = 50,
    ) -> Page[AuditView]:
        has_target = filter.target_type is not None or filter.target_id is not None
        if has_target and (filter.target_type is None or filter.target_id is None):
            raise InvalidInputError("target_type and target_id must both be provided")

        cursor_dt = None
        if cursor is not None:
            cursor_dt, _ = decode_cursor(cursor)

        async with self._ctx.admin_db.session() as session:
            if filter.target_type is not None and filter.target_id is not None:
                entries = await AuditRepository.list_by_target(
                    session,
                    filter.target_type,
                    filter.target_id,
                    limit=limit + 1,
                    cursor=cursor_dt,
                    actor_id=filter.actor_id,
                    origin=filter.origin,
                    since=filter.since,
                    until=filter.until,
                )
            elif filter.actor_id is not None:
                entries = await AuditRepository.list_by_actor(
                    session,
                    filter.actor_id,
                    limit=limit + 1,
                    cursor=cursor_dt,
                    origin=filter.origin,
                    since=filter.since,
                    until=filter.until,
                )
            else:
                entries = await AuditRepository.list_all(
                    session,
                    limit=limit + 1,
                    cursor=cursor_dt,
                    origin=filter.origin,
                    since=filter.since,
                    until=filter.until,
                )

        has_more = len(entries) > limit
        if has_more:
            entries = entries[:limit]

        views = [self._to_view(e) for e in entries]
        next_cursor = None
        if has_more and entries:
            next_cursor = encode_cursor(entries[-1].occurred_at, entries[-1].id)

        return Page(data=views, has_more=has_more, next_cursor=next_cursor)

    async def get_by_id(self, audit_id: str) -> AuditView:
        async with self._ctx.admin_db.session() as session:
            entry = await AuditRepository.get_by_id(session, audit_id)
        if entry is None:
            raise AuditEntryNotFoundError(audit_id)
        return self._to_view(entry)

    @staticmethod
    def _to_view(entry: AuditEntry) -> AuditView:
        return AuditView(
            id=entry.id,
            occurred_at=entry.occurred_at,
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            target_parent_id=entry.target_parent_id,
            actor_type=entry.actor_type,
            actor_id=entry.actor_id,
            actor_session_id=entry.actor_session_id,
            before=entry.before,
            after=entry.after,
            diff=entry.diff,
            request_id=entry.request_id,
            trace_id=entry.trace_id,
            job_id=entry.job_id,
            reason=entry.reason,
            ip_address=entry.ip_address,
            user_agent=entry.user_agent,
            origin=entry.origin,
        )
