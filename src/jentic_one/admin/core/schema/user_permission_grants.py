"""UserPermissionGrant ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AdminBase, AuditableMixin
from jentic_one.shared.db.ids import generate_ksuid
from jentic_one.shared.db.types import UTCDateTime
from jentic_one.shared.db.utils import utcnow


class UserPermissionGrant(AuditableMixin, AdminBase):
    """Maps a permission grant to a user."""

    __tablename__ = "user_permission_grants"
    __table_args__ = (
        UniqueConstraint("user_id", "permission", name="uq_user_permission_grants_user_perm"),
        Index("ix_user_permission_grants_permission", "permission"),
    )

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("perm"),
        server_default=func.generate_ksuid("perm"),
    )
    user_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission: Mapped[str] = mapped_column(String(64), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utcnow, server_default=func.now()
    )
    granted_by: Mapped[str | None] = mapped_column(String(30), nullable=True)
