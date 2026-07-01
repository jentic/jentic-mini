"""OperationURLIndex ORM model — pre-computed URL matching index for operations."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AuditableMixin, RegistryBase
from jentic_one.shared.db.ids import new_uuid
from jentic_one.shared.db.types import GUID, text_array_variant

if TYPE_CHECKING:
    from jentic_one.registry.core.schema.api_revisions import ApiRevision
    from jentic_one.registry.core.schema.operations import Operation


class OperationURLIndex(AuditableMixin, RegistryBase):
    """Pre-computed URL matching index for reverse-lookup of operations."""

    __tablename__ = "operation_url_indexes"
    __table_args__ = (
        UniqueConstraint(
            "method",
            "host",
            "host_regex",
            "path_template",
            name="uq_operation_url_index_lookup",
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "ix_operation_url_index_method_host_revision",
            "method",
            "host",
            "revision_id",
            "path_template",
        ),
        Index("ix_operation_url_index_operation_id", "operation_id"),
        Index("ix_operation_url_index_revision_id", "revision_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=new_uuid,
        server_default=func.gen_random_uuid(),
    )
    operation_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("operations.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("api_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    host: Mapped[str | None] = mapped_column(Text, nullable=True)
    host_regex: Mapped[str | None] = mapped_column(Text, nullable=True)
    path_template: Mapped[str] = mapped_column(Text, nullable=False)
    path_regex: Mapped[str] = mapped_column(Text, nullable=False)
    param_names: Mapped[list[str]] = mapped_column(text_array_variant(), nullable=False)
    segment_count: Mapped[int] = mapped_column(Integer, nullable=False)

    operation: Mapped[Operation] = relationship()
    revision: Mapped[ApiRevision] = relationship()
