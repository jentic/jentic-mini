"""BasicCredential ORM model for username/password authentication."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AuditableMixin, ControlBase
from jentic_one.shared.db.ids import new_uuid
from jentic_one.shared.db.types import GUID

if TYPE_CHECKING:
    from jentic_one.control.core.schema.credentials import Credential


class BasicCredential(AuditableMixin, ControlBase):
    """Stores encrypted username/password pairs for basic authentication."""

    __tablename__ = "basic_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=new_uuid,
        server_default=func.gen_random_uuid(),
    )
    credential_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("credentials.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)

    credential: Mapped[Credential] = relationship(
        back_populates="basic_credential", lazy="selectin"
    )
