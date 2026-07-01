"""Event streaming service."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from jentic_one.admin.repos import EventRepository
from jentic_one.admin.services.schemas.events import EventView, Heartbeat
from jentic_one.shared.context import Context
from jentic_one.shared.models.events import EventSeverity


class EventStreamService:
    """Polls for new events and yields them as a transport-agnostic async stream."""

    def __init__(self, ctx: Context) -> None:
        self._ctx = ctx

    async def stream(
        self,
        since: datetime | None = None,
        last_event_id: str | None = None,
        poll_interval_seconds: float = 5.0,
        event_type: list[str] | None = None,
        severity: list[str] | None = None,
        requires_action: bool | None = None,
        trace_id: str | None = None,
        actor_id: str | None = None,
        actor_type: str | None = None,
    ) -> AsyncIterator[EventView | Heartbeat]:
        cursor: tuple[datetime, str] | None = None
        last_seen: datetime = since if since is not None else datetime.now(UTC)

        if last_event_id is not None:
            async with self._ctx.admin_db.session() as session:
                event = await EventRepository.get_by_id(session, last_event_id)
            if event is not None:
                cursor = (event.created_at, event.id)

        while True:
            # The DB session is strictly scoped to this ``async with`` block and
            # never held across the ``await asyncio.sleep`` below. Keeping the
            # session local (never stashed on ``self``) guarantees that a
            # ``CancelledError`` raised on SSE client disconnect unwinds the
            # context manager and returns the pooled connection to the engine —
            # the leak guarded against in #627.
            async with self._ctx.admin_db.session() as session:
                if cursor is not None:
                    events = await EventRepository.list_after_cursor(
                        session,
                        cursor,
                        event_type=event_type,
                        severity=severity,
                        requires_action=requires_action,
                        trace_id=trace_id,
                        actor_id=actor_id,
                        actor_type=actor_type,
                    )
                else:
                    events = await EventRepository.list_since(
                        session,
                        last_seen,
                        event_type=event_type,
                        severity=severity,
                        requires_action=requires_action,
                        trace_id=trace_id,
                        actor_id=actor_id,
                        actor_type=actor_type,
                    )

            if events:
                for event in events:
                    yield EventView(
                        id=event.id,
                        type=event.type,
                        severity=EventSeverity(event.severity),
                        summary=event.summary,
                        requires_action=event.requires_action,
                        acknowledged=event.acknowledged,
                        acknowledged_at=event.acknowledged_at,
                        acknowledged_by=event.acknowledged_by,
                        trace_id=event.trace_id,
                        detail=event.detail,
                        data=event.data,
                        execution_id=event.execution_id,
                        job_id=event.job_id,
                        actor_id=event.actor_id,
                        actor_type=event.actor_type,
                        created_at=event.created_at,
                    )
                cursor = (events[-1].created_at, events[-1].id)
            else:
                yield Heartbeat(sent_at=datetime.now(UTC))

            await asyncio.sleep(poll_interval_seconds)
