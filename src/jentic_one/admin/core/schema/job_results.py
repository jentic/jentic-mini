"""JobResult ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AdminBase, AuditableMixin
from jentic_one.shared.db.ids import generate_ksuid
from jentic_one.shared.db.types import UTCDateTime, json_variant


class JobResult(AuditableMixin, AdminBase):
    """Stores the output of a completed job."""

    __tablename__ = "job_results"
    __table_args__ = (Index("ix_job_results_available_until", "available_until"),)

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("jres"),
        server_default=func.generate_ksuid("jres"),
    )
    job_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    body: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        json_variant(), nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    available_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
