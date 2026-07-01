"""Event ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AdminBase, AuditableMixin
from jentic_one.shared.db.ids import generate_ksuid
from jentic_one.shared.db.types import UTCDateTime, json_variant


class Event(AuditableMixin, AdminBase):
    """Platform event for operational monitoring and alerting."""

    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_created_at", "created_at"),
        Index("ix_events_type_created", "type", "created_at"),
        Index("ix_events_severity_created", "severity", "created_at"),
        Index(
            "ix_events_requires_action_unack",
            "requires_action",
            postgresql_where=text("requires_action AND NOT acknowledged"),
        ),
        Index(
            "ix_events_trace_id",
            "trace_id",
            postgresql_where=text("trace_id IS NOT NULL"),
        ),
        Index("ix_events_actor", "actor_id", "actor_type"),
    )

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("evt"),
        server_default=func.generate_ksuid("evt"),
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    requires_action: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(30), nullable=True)
    acknowledgement_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary: Mapped[str] = mapped_column(String(512), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        json_variant(), nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    execution_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
