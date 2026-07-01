"""CustomerAPIKey ORM model for storing encrypted API keys."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AuditableMixin, ControlBase
from jentic_one.shared.db.ids import generate_ksuid
from jentic_one.shared.db.types import UTCDateTime

if TYPE_CHECKING:
    from jentic_one.control.core.schema.credentials import Credential


class CustomerAPIKey(AuditableMixin, ControlBase):
    """Stores an encrypted API key associated with a credential."""

    __tablename__ = "customer_api_keys"

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("cak"),
        server_default=func.generate_ksuid("cak"),
    )
    credential_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("credentials.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    key_preview: Mapped[str | None] = mapped_column(String(16), nullable=True)
    location: Mapped[str] = mapped_column(
        String(20), nullable=False, default="header", server_default=text("'header'")
    )
    field_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Authorization", server_default=text("'Authorization'")
    )
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    credential: Mapped[Credential] = relationship(back_populates="customer_api_key")
