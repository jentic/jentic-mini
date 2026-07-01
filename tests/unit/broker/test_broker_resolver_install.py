"""Test that _build_app installs the registry resolver before DB startup.

Regression test for #526: the standalone broker returned 500 on /execute because
the resolver install was gated on ``ctx.has_db("registry")`` (requires a live
connection) instead of ``ctx.is_db_allowed("registry")`` (configuration check).
"""

from __future__ import annotations

from typing import Any

import pytest

from jentic_one.__main__ import _build_app
from jentic_one.shared.broker.protocols import RegistryResolverProtocol
from jentic_one.shared.config import AppConfig
from jentic_one.shared.context import Context


@pytest.fixture()
def app_config(sample_config_dict: dict[str, Any]) -> AppConfig:
    return AppConfig.model_validate(sample_config_dict)


def test_resolver_installed_before_db_startup(app_config: AppConfig) -> None:
    ctx = Context(app_config, allowed_dbs={"broker", "admin", "control", "registry"})

    assert ctx.has_db("registry") is False

    app = _build_app(ctx, ["broker"])

    assert hasattr(app.state, "broker_registry_resolver")
    assert isinstance(app.state.broker_registry_resolver, RegistryResolverProtocol)


def test_resolver_not_installed_when_registry_not_allowed(app_config: AppConfig) -> None:
    ctx = Context(app_config, allowed_dbs={"broker", "admin", "control"})

    app = _build_app(ctx, ["broker"])

    assert not hasattr(app.state, "broker_registry_resolver")
