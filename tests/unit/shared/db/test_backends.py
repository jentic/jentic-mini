"""Tests for pluggable database backend selection and engine wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from jentic_one.shared.config import DatabaseConfig
from jentic_one.shared.db.backends import (
    PostgresBackend,
    SqliteBackend,
    configure_sqlite_pragmas,
    get_backend,
)


def test_get_backend_returns_postgres_by_default() -> None:
    config = DatabaseConfig(name="reg")
    backend = get_backend(config)
    assert isinstance(backend, PostgresBackend)
    assert backend.dialect_name == "postgres"


def test_get_backend_returns_sqlite() -> None:
    config = DatabaseConfig(backend="sqlite", path=":memory:")
    backend = get_backend(config)
    assert isinstance(backend, SqliteBackend)
    assert backend.dialect_name == "sqlite"


def test_postgres_config_requires_name() -> None:
    with pytest.raises(ValueError, match="requires a database 'name'"):
        DatabaseConfig(backend="postgres", name="")


def test_sqlite_config_requires_path() -> None:
    with pytest.raises(ValueError, match="requires a 'path'"):
        DatabaseConfig(backend="sqlite")


def test_postgres_make_url_and_engine_kwargs() -> None:
    config = DatabaseConfig(name="reg", schema_name="registry")
    backend = PostgresBackend()
    url = backend.make_url(config)
    assert url.drivername == "postgresql+asyncpg"
    assert url.database == "reg"
    kwargs = backend.engine_kwargs(config)
    assert kwargs["connect_args"]["server_settings"]["search_path"] == "registry,public"


def test_sqlite_make_url_uses_path() -> None:
    config = DatabaseConfig(backend="sqlite", path="/tmp/x.db")
    backend = SqliteBackend()
    url = backend.make_url(config)
    assert url.drivername == "sqlite+aiosqlite"
    assert url.database == "/tmp/x.db"


@pytest.mark.asyncio
async def test_sqlite_engine_round_trip() -> None:
    config = DatabaseConfig(backend="sqlite", path=":memory:")
    backend = SqliteBackend()
    engine = create_async_engine(backend.make_url(config), **backend.engine_kwargs(config))
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_sqlite_connect_hook_sets_wal_and_busy_timeout(tmp_path: Path) -> None:
    """The connect hook applies journal_mode=WAL and the configured busy_timeout.

    Uses a file-backed DB (not ``:memory:``) because WAL is a no-op for in-memory
    databases.
    """
    db_file = tmp_path / "pragma_test.db"
    config = DatabaseConfig(backend="sqlite", path=str(db_file), busy_timeout_ms=7321)
    backend = SqliteBackend()
    engine = create_async_engine(backend.make_url(config), **backend.engine_kwargs(config))
    configure_sqlite_pragmas(
        engine,
        journal_mode=config.journal_mode,
        busy_timeout_ms=config.busy_timeout_ms,
    )
    try:
        async with engine.connect() as conn:
            journal_mode = (await conn.execute(text("PRAGMA journal_mode"))).scalar_one()
            busy_timeout = (await conn.execute(text("PRAGMA busy_timeout"))).scalar_one()
            foreign_keys = (await conn.execute(text("PRAGMA foreign_keys"))).scalar_one()
        assert journal_mode == "wal"
        assert busy_timeout == 7321
        assert foreign_keys == 1
    finally:
        await engine.dispose()
