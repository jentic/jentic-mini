"""SpecFile ORM model — stores parsed spec file content per revision."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AuditableMixin, RegistryBase
from jentic_one.shared.db.ids import new_uuid
from jentic_one.shared.db.types import GUID, json_variant

if TYPE_CHECKING:
    from jentic_one.registry.core.schema.api_revisions import ApiRevision


class SpecFile(AuditableMixin, RegistryBase):
    """A parsed spec file belonging to an API revision."""

    __tablename__ = "spec_files"
    __table_args__ = (
        UniqueConstraint("revision_id", "filename", name="uq_spec_files_revision_id_filename"),
        Index("ix_spec_files_revision_id", "revision_id"),
        Index("ix_spec_files_source_id", "source_id"),
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
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[dict] = mapped_column(json_variant(), nullable=False)  # type: ignore[type-arg]
    sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    revision: Mapped[ApiRevision] = relationship(back_populates="spec_files")
