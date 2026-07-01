"""SQLite database backend (aiosqlite).

SQLite is an embedded production target. Foreign-key enforcement is enabled
per-connection via a PRAGMA.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import URL
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import ConnectionPoolEntry

from jentic_one.shared.config import DatabaseConfig
from jentic_one.shared.db.backends.base import DatabaseBackend


class SqliteBackend(DatabaseBackend):
    """Backend for SQLite using the aiosqlite driver."""

    @property
    def dialect_name(self) -> str:
        return "sqlite"

    def make_url(self, config: DatabaseConfig) -> URL:
        # config.path is validated to be non-None for the sqlite backend.
        database = config.path or ":memory:"
        return URL.create(drivername="sqlite+aiosqlite", database=database)

    def engine_kwargs(self, config: DatabaseConfig) -> dict[str, Any]:
        return {
            "connect_args": {"check_same_thread": False},
        }


def configure_sqlite_pragmas(
    engine: AsyncEngine,
    *,
    journal_mode: str = "WAL",
    busy_timeout_ms: int = 5000,
) -> None:
    """Register a hook setting per-connection SQLite PRAGMAs.

    Runs, in order, on every new connection:

    - ``PRAGMA foreign_keys=ON`` — enforce referential integrity (SQLite leaves
      this off by default).
    - ``PRAGMA journal_mode=<journal_mode>`` — ``WAL`` lets a writer and readers
      proceed concurrently. This is persistent per database file (a no-op after
      the first set) and a no-op for ``:memory:`` databases.
    - ``PRAGMA busy_timeout=<busy_timeout_ms>`` — when a write meets a held lock,
      wait up to this many milliseconds for it to clear instead of failing
      immediately with ``database is locked``. This is per-connection, so it is
      issued on every connect.
    """

    sync_engine = engine.sync_engine

    @event.listens_for(sync_engine, "connect")
    def _set_pragma(dbapi_connection: DBAPIConnection, _record: ConnectionPoolEntry) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA journal_mode={journal_mode}")
        cursor.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        cursor.close()


def enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    """Backwards-compatible alias that configures pragmas with defaults."""
    configure_sqlite_pragmas(engine)
