"""UserSecret ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AdminBase, AuditableMixin
from jentic_one.shared.db.ids import generate_ksuid
from jentic_one.shared.db.types import UTCDateTime


class UserSecret(AuditableMixin, AdminBase):
    """Stores user authentication secrets (password hash, lockout state)."""

    __tablename__ = "user_secrets"

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("usec"),
        server_default=func.generate_ksuid("usec"),
    )
    user_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_algo: Mapped[str] = mapped_column(String(32), nullable=False)
    password_changed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
