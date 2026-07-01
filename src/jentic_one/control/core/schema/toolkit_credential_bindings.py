"""ToolkitCredentialBinding ORM model — junction table linking toolkits to credentials."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AuditableMixin, ControlBase
from jentic_one.shared.db.ids import generate_ksuid
from jentic_one.shared.db.types import UTCDateTime
from jentic_one.shared.db.utils import utcnow

if TYPE_CHECKING:
    from jentic_one.control.core.schema.credentials import Credential
    from jentic_one.control.core.schema.toolkits import Toolkit


class ToolkitCredentialBinding(AuditableMixin, ControlBase):
    """Associates a toolkit with a credential."""

    __tablename__ = "toolkit_credential_bindings"
    __table_args__ = (
        UniqueConstraint("toolkit_id", "credential_id", name="uq_toolkit_credential_binding"),
    )

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("tcb"),
        server_default=func.generate_ksuid("tcb"),
    )
    toolkit_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("toolkits.id", ondelete="CASCADE"),
        nullable=False,
    )
    credential_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("credentials.id", ondelete="CASCADE"),
        nullable=False,
    )
    bound_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utcnow, server_default=func.now()
    )

    toolkit: Mapped[Toolkit] = relationship(back_populates="bindings")
    credential: Mapped[Credential] = relationship(lazy="selectin")
