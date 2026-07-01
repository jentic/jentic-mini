"""Tests for the Context class.

Context lifecycle tests that require real database connections live in
tests/integration/test_db_connectivity.py and tests/integration/test_context_lifecycle.py.
"""

from __future__ import annotations

from typing import Any

import pytest

from jentic_one.shared.config import AppConfig
from jentic_one.shared.context import Context
from jentic_one.shared.db import DatabaseSession


@pytest.fixture()
def app_config(sample_config_dict: dict[str, Any]) -> AppConfig:
    return AppConfig.model_validate(sample_config_dict)


def test_creates_from_config(app_config: AppConfig) -> None:
    ctx = Context(app_config)
    assert ctx.config is app_config


def test_db_properties_are_lazy(app_config: AppConfig) -> None:
    ctx = Context(app_config)
    assert ctx._registry_db is None
    assert ctx._admin_db is None
    assert ctx._control_db is None


def test_db_properties_return_database_session_on_access(app_config: AppConfig) -> None:
    ctx = Context(app_config)
    assert isinstance(ctx.registry_db, DatabaseSession)
    assert isinstance(ctx.admin_db, DatabaseSession)
    assert isinstance(ctx.control_db, DatabaseSession)


def test_db_property_returns_same_instance(app_config: AppConfig) -> None:
    ctx = Context(app_config)
    first = ctx.registry_db
    second = ctx.registry_db
    assert first is second


def test_allowed_dbs_restricts_access(app_config: AppConfig) -> None:
    ctx = Context(app_config, allowed_dbs={"registry", "admin"})
    assert isinstance(ctx.registry_db, DatabaseSession)
    assert isinstance(ctx.admin_db, DatabaseSession)
    with pytest.raises(RuntimeError, match="not allowed"):
        _ = ctx.control_db


def test_disallowed_db_raises_descriptive_error(app_config: AppConfig) -> None:
    ctx = Context(app_config, allowed_dbs={"control"})
    with pytest.raises(RuntimeError, match=r"'registry'.*not allowed"):
        _ = ctx.registry_db
    with pytest.raises(RuntimeError, match=r"'admin'.*not allowed"):
        _ = ctx.admin_db


def test_none_allowed_dbs_allows_all(app_config: AppConfig) -> None:
    ctx = Context(app_config, allowed_dbs=None)
    assert isinstance(ctx.registry_db, DatabaseSession)
    assert isinstance(ctx.admin_db, DatabaseSession)
    assert isinstance(ctx.control_db, DatabaseSession)


def test_empty_set_blocks_all(app_config: AppConfig) -> None:
    ctx = Context(app_config, allowed_dbs=set())
    with pytest.raises(RuntimeError, match="not allowed"):
        _ = ctx.registry_db
    with pytest.raises(RuntimeError, match="not allowed"):
        _ = ctx.admin_db
    with pytest.raises(RuntimeError, match="not allowed"):
        _ = ctx.control_db


def test_single_db_allowed(app_config: AppConfig) -> None:
    ctx = Context(app_config, allowed_dbs={"admin"})
    assert isinstance(ctx.admin_db, DatabaseSession)
    with pytest.raises(RuntimeError, match="not allowed"):
        _ = ctx.registry_db
    with pytest.raises(RuntimeError, match="not allowed"):
        _ = ctx.control_db
