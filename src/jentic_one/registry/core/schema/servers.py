"""Server and ServerVariable ORM models — API base URLs and their template variables."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AuditableMixin, RegistryBase
from jentic_one.shared.db.ids import new_uuid
from jentic_one.shared.db.types import GUID, json_variant

if TYPE_CHECKING:
    from jentic_one.registry.core.schema.api_revisions import ApiRevision


class Server(AuditableMixin, RegistryBase):
    """A base URL for an API revision or a specific operation."""

    __tablename__ = "servers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["operation_id"],
            ["operations.id"],
            name="fk_servers_operation_id",
            ondelete="CASCADE",
            use_alter=True,
        ),
        Index("ix_servers_revision_id", "revision_id"),
        Index("ix_servers_operation_id", "operation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=new_uuid,
        server_default=func.gen_random_uuid(),
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("api_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    operation_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    revision: Mapped[ApiRevision] = relationship(back_populates="servers")
    variables: Mapped[list[ServerVariable]] = relationship(
        back_populates="server", cascade="all, delete-orphan", lazy="joined"
    )


class ServerVariable(AuditableMixin, RegistryBase):
    """A template variable for a server URL."""

    __tablename__ = "server_variables"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=new_uuid,
        server_default=func.gen_random_uuid(),
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enum: Mapped[Any | None] = mapped_column(json_variant(), nullable=True)
    extensions: Mapped[dict | None] = mapped_column(json_variant(), nullable=True)  # type: ignore[type-arg]

    server: Mapped[Server] = relationship(back_populates="variables")
