"""Base protocol for operation text projection strategies."""

from __future__ import annotations

from typing import Protocol

from jentic_one.registry.core.schema.operations import Operation


class Projection(Protocol):
    """Protocol for operation text projection strategies."""

    def create_projection(self, operation: Operation, vendor_id: str, api_name: str) -> str:
        """Create text projection for an operation."""
        ...
