"""SecurityScheme and SecuritySchemeFlow ORM models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AuditableMixin, RegistryBase
from jentic_one.shared.db.ids import new_uuid
from jentic_one.shared.db.types import GUID, json_variant

if TYPE_CHECKING:
    from jentic_one.registry.core.schema.api_revisions import ApiRevision


class SecurityScheme(AuditableMixin, RegistryBase):
    """An API security scheme defined in a revision's spec."""

    __tablename__ = "security_schemes"
    __table_args__ = (
        UniqueConstraint("revision_id", "name", name="uq_security_schemes_revision_name"),
        Index("ix_security_schemes_revision_id", "revision_id"),
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheme: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bearer_format: Mapped[str | None] = mapped_column(String(50), nullable=True)
    in_location: Mapped[str | None] = mapped_column("in", String(50), nullable=True)
    param_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    open_id_connect_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_scheme: Mapped[dict] = mapped_column(json_variant(), nullable=False)  # type: ignore[type-arg]

    revision: Mapped[ApiRevision] = relationship(back_populates="security_schemes")
    flows: Mapped[list[SecuritySchemeFlow]] = relationship(
        back_populates="security_scheme", cascade="all, delete-orphan", lazy="selectin"
    )


class SecuritySchemeFlow(AuditableMixin, RegistryBase):
    """An OAuth2 flow within a security scheme."""

    __tablename__ = "security_scheme_flows"
    __table_args__ = (Index("ix_security_scheme_flows_scheme_id", "security_scheme_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=new_uuid,
        server_default=func.gen_random_uuid(),
    )
    security_scheme_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("security_schemes.id", ondelete="CASCADE"),
        nullable=False,
    )
    flow_type: Mapped[str] = mapped_column(String(50), nullable=False)
    authorization_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[dict | None] = mapped_column(json_variant(), nullable=True)  # type: ignore[type-arg]
    raw_flow: Mapped[dict] = mapped_column(json_variant(), nullable=False)  # type: ignore[type-arg]

    security_scheme: Mapped[SecurityScheme] = relationship(back_populates="flows")
