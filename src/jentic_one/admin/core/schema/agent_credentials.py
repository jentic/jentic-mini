"""AgentCredential ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AdminBase, AuditableMixin
from jentic_one.shared.db.ids import generate_ksuid
from jentic_one.shared.db.types import UTCDateTime


class AgentCredential(AuditableMixin, AdminBase):
    """Stores hashed credentials for agent authentication."""

    __tablename__ = "agent_credentials"
    __table_args__ = (Index("ix_agent_credentials_agent_id", "agent_id", unique=True),)

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("agc"),
        server_default=func.generate_ksuid("agc"),
    )
    agent_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_secret_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    api_key_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rotated_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
