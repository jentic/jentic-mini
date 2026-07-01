"""Integration tests for Context lifecycle using real database connections."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from jentic_one.shared.config import AppConfig
from jentic_one.shared.context import Context

pytestmark = pytest.mark.integration


async def test_async_context_manager(integration_config: AppConfig) -> None:
    async with Context(integration_config) as ctx:
        assert ctx.registry_db.engine is not None
        assert ctx.admin_db.engine is not None
        assert ctx.control_db.engine is not None


async def test_startup_connects_all_dbs(integration_config: AppConfig) -> None:
    ctx = Context(integration_config)
    await ctx.startup()
    assert ctx.registry_db.engine is not None
    await ctx.shutdown()


async def test_shutdown_disposes_engines(integration_config: AppConfig) -> None:
    ctx = Context(integration_config)
    await ctx.startup()
    await ctx.shutdown()
    assert ctx._registry_db is not None
    assert ctx._registry_db._engine is None


async def test_bad_config_fails_on_first_query() -> None:
    """Connection to a non-existent host fails when the pool first connects."""
    bad_config = AppConfig.model_validate(
        {
            "databases": {
                "registry": {
                    "host": "localhost",
                    "port": 19999,
                    "name": "nonexistent",
                    "user": "bad_user",
                    "password": "bad_pass",
                    "pool_max": 1,
                    "schema_name": "public",
                },
                "admin": {
                    "host": "localhost",
                    "port": 19998,
                    "name": "nonexistent",
                    "user": "bad_user",
                    "password": "bad_pass",
                    "pool_max": 1,
                    "schema_name": "public",
                },
                "control": {
                    "host": "localhost",
                    "port": 19997,
                    "name": "nonexistent",
                    "user": "bad_user",
                    "password": "bad_pass",
                    "pool_max": 1,
                    "schema_name": "public",
                },
            },
        }
    )
    ctx = Context(bad_config)
    await ctx.startup()
    with pytest.raises(OSError):
        async with ctx.registry_db.session() as session:
            await session.execute(text("SELECT 1"))
    await ctx.shutdown()


async def test_startup_only_connects_allowed_dbs(integration_config: AppConfig) -> None:
    ctx = Context(integration_config, allowed_dbs={"registry"})
    await ctx.startup()
    assert ctx._registry_db is not None
    assert ctx._admin_db is None
    assert ctx._control_db is None
    await ctx.shutdown()
