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


def enable_sqlite_immediate_begin(engine: AsyncEngine) -> None:
    """Make SQLite transactions begin with ``BEGIN IMMEDIATE``.

    By default pysqlite/aiosqlite open transactions in *deferred* mode: the
    write lock is only acquired when the first write statement runs. A
    transaction that reads first (e.g. ``UPDATE ... WHERE id = (SELECT ...)``)
    therefore holds a read snapshot and then tries to *upgrade* to a writer. If
    another connection has committed a write in the meantime, SQLite raises
    ``SQLITE_BUSY_SNAPSHOT`` ("database is locked") *immediately* — ``PRAGMA
    busy_timeout`` does not apply to snapshot-upgrade conflicts, only to
    acquiring an initial lock.

    Emitting ``BEGIN IMMEDIATE`` takes the write lock up front, so there is no
    read→write upgrade to fail on and ``busy_timeout`` governs the wait. This
    serialises writers (the price of SQLite) but eliminates the spurious
    "database is locked" errors between concurrent writers such as the job
    worker and request handlers.
    """

    sync_engine = engine.sync_engine

    @event.listens_for(sync_engine, "connect")
    def _disable_pysqlite_implicit_begin(
        dbapi_connection: DBAPIConnection, _record: ConnectionPoolEntry
    ) -> None:
        # Stop the DBAPI from emitting its own implicit (deferred) BEGIN so we
        # can control transaction start with the event below.
        dbapi_connection.isolation_level = None

    @event.listens_for(sync_engine, "begin")
    def _emit_begin_immediate(conn: Any) -> None:
        conn.exec_driver_sql("BEGIN IMMEDIATE")


def enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    """Backwards-compatible alias that configures pragmas with defaults."""
    configure_sqlite_pragmas(engine)
