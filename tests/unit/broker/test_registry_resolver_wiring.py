"""Unit tests for the broker registry-resolver composition wiring.

Verifies the in-process resolver satisfies ``RegistryResolverProtocol`` and that
``install_broker_registry_resolver`` injects it onto broker app state, so the
broker can resolve URLs without importing ``jentic_one.registry``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from fastapi import FastAPI

from jentic_one.shared.broker.protocols import RegistryResolverProtocol
from jentic_one.wiring import InProcessRegistryResolver, install_broker_registry_resolver


def test_in_process_resolver_satisfies_protocol() -> None:
    resolver = InProcessRegistryResolver(MagicMock())
    assert isinstance(resolver, RegistryResolverProtocol)


def test_install_sets_broker_registry_resolver_on_app_state() -> None:
    app = FastAPI()
    ctx: Any = MagicMock()

    install_broker_registry_resolver(app, ctx)

    assert isinstance(app.state.broker_registry_resolver, InProcessRegistryResolver)
    assert isinstance(app.state.broker_registry_resolver, RegistryResolverProtocol)
