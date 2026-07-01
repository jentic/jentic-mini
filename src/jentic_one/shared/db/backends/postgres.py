"""PostgreSQL database backend (asyncpg)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import URL

from jentic_one.shared.config import DatabaseConfig
from jentic_one.shared.db.backends.base import DatabaseBackend


class PostgresBackend(DatabaseBackend):
    """Backend for PostgreSQL using the asyncpg driver."""

    @property
    def dialect_name(self) -> str:
        return "postgres"

    def make_url(self, config: DatabaseConfig) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=config.user,
            password=config.password.get_secret_value(),
            host=config.host,
            port=config.port,
            database=config.name,
        )

    def engine_kwargs(self, config: DatabaseConfig) -> dict[str, Any]:
        return {
            "pool_size": config.pool_max,
            "pool_pre_ping": True,
            "connect_args": {"server_settings": {"search_path": f"{config.schema_name},public"}},
        }
