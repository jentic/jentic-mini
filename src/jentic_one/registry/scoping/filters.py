"""Registry-surface access filter builder for dynamic query scoping."""

from __future__ import annotations

from sqlalchemy.sql.elements import ColumnElement

from jentic_one.registry.core.schema.notes import Note
from jentic_one.shared.auth.identity import Identity

ORG_ADMIN = "org:admin"


def build_access_filters(identity: Identity, model: type[Note]) -> list[ColumnElement[bool]]:
    """Build SQLAlchemy filter expressions scoping queries to the caller's visibility.

    Rules (evaluated in order):
    1. org:admin → no restriction (empty list).
    2. Otherwise → created_by == self.
    """
    if ORG_ADMIN in identity.permissions:
        return []

    if not identity.sub:
        return []

    if model is Note:
        return [Note.created_by == identity.sub]

    return []
