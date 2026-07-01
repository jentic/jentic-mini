"""Note ORM model — annotations attached to registry resources."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AuditableMixin, RegistryBase
from jentic_one.shared.db.ids import generate_ksuid
from jentic_one.shared.db.types import GUID

if TYPE_CHECKING:
    from jentic_one.registry.core.schema.apis import Api


class Note(AuditableMixin, RegistryBase):
    """An annotation attached to a registry resource (API, operation, execution, credential)."""

    __tablename__ = "notes"
    __table_args__ = (
        Index("ix_notes_created_at_id", "created_at", "id"),
        Index("ix_notes_resource_api_id", "resource_api_id"),
        Index("ix_notes_resource_operation_id", "resource_operation_id"),
        Index("ix_notes_resource_execution_id", "resource_execution_id"),
        Index("ix_notes_resource_credential_id", "resource_credential_id"),
        Index("ix_notes_created_by", "created_by"),
    )

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("note"),
        server_default=func.generate_ksuid("note"),
    )
    resource_api_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("apis.id", ondelete="CASCADE"),
        nullable=True,
    )
    resource_operation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_execution_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_credential_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence_source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'client'"), default="client"
    )
    source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Notes always carry an author; override the AuditableMixin's relaxed
    # (temporarily nullable) created_by to keep it required.
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    related_execution_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    api: Mapped[Api | None] = relationship("Api", lazy="raise")
