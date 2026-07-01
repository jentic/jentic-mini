"""Operation ORM model — individual API endpoints within a revision."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jentic_one.shared.db.base import AuditableMixin, RegistryBase
from jentic_one.shared.db.types import (
    GUID,
    json_variant,
    string_array_variant,
)

if TYPE_CHECKING:
    from jentic_one.registry.core.schema.api_revisions import ApiRevision
    from jentic_one.registry.core.schema.servers import Server


class Operation(AuditableMixin, RegistryBase):
    """An individual API endpoint (path + method) within a revision."""

    __tablename__ = "operations"
    __table_args__ = (
        UniqueConstraint(
            "revision_id", "path", "method", name="uq_operations_revision_path_method"
        ),
        UniqueConstraint("revision_id", "operation_id", name="uq_operations_revision_operation_id"),
        Index("ix_operations_revision_id", "revision_id"),
        Index("ix_operations_operation_id", "operation_id"),
        Index("ix_operations_tags", "tags", postgresql_using="gin"),
        Index("ix_operations_revision_id_created_at_id", "revision_id", "created_at", "id"),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    revision_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("api_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    operation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(string_array_variant(), nullable=True)
    deprecated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    raw_operation: Mapped[dict | None] = mapped_column(json_variant(), nullable=True)  # type: ignore[type-arg]

    search_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    revision: Mapped[ApiRevision] = relationship(back_populates="operations")
    servers: Mapped[list[Server]] = relationship(
        primaryjoin="Server.operation_id == Operation.id",
        viewonly=True,
        lazy="joined",
    )
    version_servers: Mapped[list[Server]] = relationship(
        primaryjoin=(
            "and_(Server.revision_id == Operation.revision_id, Server.operation_id == None)"
        ),
        foreign_keys="[Server.revision_id]",
        viewonly=True,
        lazy="joined",
    )
