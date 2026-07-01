"""TokenValueCredential ORM model for bearer/session token storage."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AuditableMixin, ControlBase
from jentic_one.shared.db.ids import new_uuid
from jentic_one.shared.db.types import GUID, UTCDateTime

if TYPE_CHECKING:
    from jentic_one.control.core.schema.credentials import Credential


class TokenValueCredential(AuditableMixin, ControlBase):
    """Stores an encrypted bearer or session token value."""

    __tablename__ = "token_value_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=new_uuid,
        server_default=func.gen_random_uuid(),
    )
    credential_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("credentials.id", ondelete="CASCADE"),
        index=True,
    )
    encrypted_token_value: Mapped[str] = mapped_column(Text, nullable=False)
    token_preview: Mapped[str | None] = mapped_column(String(16), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    credential: Mapped[Credential] = relationship(
        back_populates="token_value_credential", lazy="selectin"
    )
