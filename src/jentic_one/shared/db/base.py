"""Declarative bases for ORM models, one per database."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import String
from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.types import UTCDateTime


def _updated_at_default(context: DefaultExecutionContext) -> dt.datetime:
    """Default for updated_at: mirror created_at so unedited rows compare equal."""
    created = context.get_current_parameters().get("created_at")  # type: ignore[no-untyped-call]
    if isinstance(created, dt.datetime):
        return created
    return dt.datetime.now(dt.UTC)


class AuditableMixin:
    """Mixin to add consistent audit tracking fields to any declarative model."""

    created_at: Mapped[dt.datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: dt.datetime.now(dt.UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    updated_at: Mapped[dt.datetime] = mapped_column(
        UTCDateTime(),
        default=_updated_at_default,
        onupdate=lambda: dt.datetime.now(dt.UTC),
        server_default=func.now(),
        nullable=False,
    )
    # TODO: Revert this to nullable=False, once we have repo/services/identity-management
    created_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )


class RegistryBase(DeclarativeBase):
    """Declarative base for registry database models."""


class ControlBase(DeclarativeBase):
    """Declarative base for control database models."""


class AdminBase(DeclarativeBase):
    """Declarative base for admin database models."""
