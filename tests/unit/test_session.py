"""Tests for DatabaseSession and get_database_url."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.engine import URL

from jentic_one.shared.config import AppConfig, DatabaseConfig
from jentic_one.shared.db.session import DatabaseSession, get_database_url


@pytest.fixture()
def db_config(sample_config_dict: dict[str, Any]) -> DatabaseConfig:
    app = AppConfig.model_validate(sample_config_dict)
    return app.databases.registry


def test_get_database_url_returns_url_object(db_config: DatabaseConfig):
    url = get_database_url(db_config)
    assert isinstance(url, URL)


def test_get_database_url_driver(db_config: DatabaseConfig):
    url = get_database_url(db_config)
    assert url.drivername == "postgresql+asyncpg"


def test_get_database_url_host_and_port(db_config: DatabaseConfig):
    url = get_database_url(db_config)
    assert url.host == "db.local"
    assert url.port == 5432


def test_get_database_url_database_name(db_config: DatabaseConfig):
    url = get_database_url(db_config)
    assert url.database == "jentic"


def test_get_database_url_username(db_config: DatabaseConfig):
    url = get_database_url(db_config)
    assert url.username == "reg_user"


def test_engine_raises_when_not_connected(db_config: DatabaseConfig):
    ds = DatabaseSession(db_config)
    with pytest.raises(RuntimeError, match="not connected"):
        _ = ds.engine


def test_session_factory_raises_when_not_connected(db_config: DatabaseConfig):
    ds = DatabaseSession(db_config)
    with pytest.raises(RuntimeError, match="not connected"):
        _ = ds.session_factory
