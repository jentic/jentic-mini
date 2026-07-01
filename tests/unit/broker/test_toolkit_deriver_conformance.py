"""Protocol conformance test for ToolkitBindingResolver."""

from __future__ import annotations

from unittest.mock import MagicMock

from jentic_one.broker.repos.toolkit_binding_resolver import ToolkitBindingResolver
from jentic_one.shared.broker.protocols import ToolkitDeriverProtocol


def test_toolkit_binding_resolver_satisfies_protocol() -> None:
    resolver = ToolkitBindingResolver(MagicMock(), MagicMock())
    assert isinstance(resolver, ToolkitDeriverProtocol)
