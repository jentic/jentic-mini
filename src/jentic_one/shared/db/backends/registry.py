"""Backend selection registry."""

from __future__ import annotations

from jentic_one.shared.config import DatabaseConfig
from jentic_one.shared.db.backends.base import DatabaseBackend
from jentic_one.shared.db.backends.postgres import PostgresBackend
from jentic_one.shared.db.backends.sqlite import SqliteBackend


def get_backend(config: DatabaseConfig) -> DatabaseBackend:
    """Return the ``DatabaseBackend`` for the configured backend."""
    match config.backend:
        case "postgres":
            return PostgresBackend()
        case "sqlite":
            return SqliteBackend()
        case other:  # pragma: no cover - guarded by config validation
            raise ValueError(f"unsupported database backend: {other!r}")
