"""AuditEntry ORM model for append-only audit log."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AdminBase
from jentic_one.shared.db.ids import generate_ksuid
from jentic_one.shared.db.types import UTCDateTime, json_variant
from jentic_one.shared.db.utils import utcnow


class AuditEntry(AdminBase):
    """Append-only audit log entry for admin mutations.

    Intentionally does not use :class:`AuditableMixin`: audit entries are
    append-only and must never carry an ``updated_at`` column. They still
    record ``created_at``/``created_by`` for provenance.
    """

    __tablename__ = "audit_entries"
    __table_args__ = (
        Index("ix_audit_target", "target_type", "target_id", "occurred_at"),
        Index("ix_audit_actor", "actor_id", "occurred_at"),
        Index("ix_audit_occurred_at", "occurred_at"),
        Index(
            "ix_audit_trace",
            "trace_id",
            postgresql_where=text("trace_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("aud"),
        server_default=func.generate_ksuid("aud"),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utcnow, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utcnow, server_default=func.now(), index=True
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False)
    target_parent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    before: Mapped[dict | None] = mapped_column(json_variant(), nullable=True)  # type: ignore[type-arg]
    after: Mapped[dict | None] = mapped_column(json_variant(), nullable=True)  # type: ignore[type-arg]
    diff: Mapped[dict | None] = mapped_column(json_variant(), nullable=True)  # type: ignore[type-arg]
    request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    origin: Mapped[str | None] = mapped_column(String(20), nullable=True)
