"""InviteToken ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AdminBase, AuditableMixin
from jentic_one.shared.db.ids import generate_ksuid
from jentic_one.shared.db.types import UTCDateTime
from jentic_one.shared.db.utils import utcnow


class InviteToken(AuditableMixin, AdminBase):
    """Tracks invite tokens issued to users."""

    __tablename__ = "invite_tokens"
    __table_args__ = (
        Index("ix_invite_tokens_user_id", "user_id"),
        Index("ix_invite_tokens_token_hash", "token_hash", unique=True),
        Index(
            "ix_invite_tokens_expires_at",
            "expires_at",
            postgresql_where=text("redeemed_at IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("inv"),
        server_default=func.generate_ksuid("inv"),
    )
    user_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utcnow, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    redeemed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
