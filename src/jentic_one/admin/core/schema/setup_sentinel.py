"""Setup sentinel ORM model.

A single-row table whose fixed primary key (``"singleton"``) serializes
first-admin creation. ``AuthService.bootstrap_admin`` inserts this row inside the
same transaction that creates the first user; a second concurrent caller — even
one using a different email — collides on the primary key and is rejected. This
closes the distinct-email race that ``COUNT(users) == 0`` cannot (no range lock
under READ COMMITTED) and that the unique email index does not cover.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AdminBase
from jentic_one.shared.db.types import UTCDateTime

#: The only id ever inserted — the table holds at most this one row.
SETUP_SENTINEL_ID = "singleton"


class SetupSentinel(AdminBase):
    """Single-row first-run land-grab lock (see module docstring)."""

    __tablename__ = "setup_sentinels"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: dt.datetime.now(dt.UTC),
        server_default=func.now(),
        nullable=False,
    )
