"""Database backend abstraction.

A ``DatabaseBackend`` encapsulates everything dialect-specific about
connecting to a database and the capabilities it offers, so that
``DatabaseSession`` and higher layers stay backend-neutral.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from sqlalchemy.engine import URL

from jentic_one.shared.config import DatabaseConfig


@runtime_checkable
class DatabaseBackend(Protocol):
    """Protocol implemented by each supported database backend."""

    @property
    def dialect_name(self) -> str:
        """Canonical dialect name, e.g. ``"postgres"`` or ``"sqlite"``."""
        ...

    def make_url(self, config: DatabaseConfig) -> URL:
        """Build the async SQLAlchemy URL for this backend."""
        ...

    def engine_kwargs(self, config: DatabaseConfig) -> dict[str, Any]:
        """Return keyword arguments for ``create_async_engine`` (pool, connect_args)."""
        ...
