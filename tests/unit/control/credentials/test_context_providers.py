"""Test that Context.providers is lazily built and returns a ProviderRegistry."""

from __future__ import annotations

from jentic_one.control.services.credentials.providers import ProviderRegistry, StaticProvider
from jentic_one.shared.config import AppConfig, DatabaseConfig, DatabasesConfig
from jentic_one.shared.context import Context


def _make_context() -> Context:
    cfg = AppConfig(
        databases=DatabasesConfig(
            registry=DatabaseConfig(backend="sqlite", path=":memory:"),
            admin=DatabaseConfig(backend="sqlite", path=":memory:"),
            control=DatabaseConfig(backend="sqlite", path=":memory:"),
        )
    )
    return Context(cfg)


def test_context_providers_returns_registry() -> None:
    ctx = _make_context()
    registry = ctx.providers
    assert isinstance(registry, ProviderRegistry)


def test_context_providers_includes_static() -> None:
    ctx = _make_context()
    provider = ctx.providers.get("static")
    assert isinstance(provider, StaticProvider)


def test_context_providers_is_cached() -> None:
    ctx = _make_context()
    assert ctx.providers is ctx.providers
