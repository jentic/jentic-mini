"""Dialect-portable column types.

These types let the same ORM models and migrations run on both PostgreSQL
(production, with native ``UUID``/``JSONB``/``ARRAY``) and SQLite (embedded
target, which lacks those types). Use them in both ``core/schema`` models and
Alembic migrations so the two stay in sync.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import CHAR, JSON, DateTime, String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeEngine


class GUID(TypeDecorator[uuid.UUID]):
    """Platform-independent UUID type.

    Uses PostgreSQL's native ``UUID`` type, otherwise ``CHAR(36)`` storing the
    canonical hyphenated string form. Values round-trip as :class:`uuid.UUID`.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


def json_variant() -> TypeEngine[Any]:
    """A JSON column: native ``JSONB`` on PostgreSQL, generic ``JSON`` elsewhere."""
    return JSONB().with_variant(JSON(), "sqlite")


def string_array_variant() -> TypeEngine[Any]:
    """A string-array column: native ``ARRAY`` on PostgreSQL, ``JSON`` on SQLite."""
    return ARRAY(String).with_variant(JSON(), "sqlite")


def text_array_variant() -> TypeEngine[Any]:
    """A text-array column: native ``ARRAY`` on PostgreSQL, ``JSON`` on SQLite."""
    return ARRAY(Text).with_variant(JSON(), "sqlite")


class UTCDateTime(TypeDecorator[dt.datetime]):
    """Timezone-aware ``DateTime`` that always round-trips as UTC-aware values.

    PostgreSQL's ``timestamptz`` preserves offsets natively, but SQLite has no
    real timestamp type: it stores ``DateTime(timezone=True)`` as a naive string
    and returns naive :class:`~datetime.datetime` objects. Comparing those against
    ``datetime.now(UTC)`` raises ``TypeError: can't compare offset-naive and
    offset-aware datetimes``.

    This decorator normalizes both directions:

    - On write, naive values are assumed UTC and aware values are converted to
      UTC, so the stored instant is unambiguous on every backend.
    - On read, values that come back naive (SQLite) are tagged as UTC, so callers
      always receive an offset-aware datetime.
    """

    impl = DateTime
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(timezone=True)

    def process_bind_param(self, value: Any, dialect: Dialect) -> dt.datetime | None:
        if not isinstance(value, dt.datetime):
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.UTC)
        return value.astimezone(dt.UTC)

    def process_result_value(self, value: Any, dialect: Dialect) -> dt.datetime | None:
        if not isinstance(value, dt.datetime):
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.UTC)
        return value.astimezone(dt.UTC)
