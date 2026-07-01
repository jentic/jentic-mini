"""ServiceAccountCredential ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AdminBase, AuditableMixin
from jentic_one.shared.db.ids import generate_ksuid
from jentic_one.shared.db.types import UTCDateTime


class ServiceAccountCredential(AuditableMixin, AdminBase):
    """Stores hashed credentials for service account authentication."""

    __tablename__ = "service_account_credentials"
    __table_args__ = (
        Index("ix_sa_credentials_service_account_id", "service_account_id", unique=True),
    )

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("sac"),
        server_default=func.generate_ksuid("sac"),
    )
    service_account_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("service_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_secret_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    api_key_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rotated_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
