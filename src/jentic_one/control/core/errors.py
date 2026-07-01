"""Core domain exceptions for the control module — importable by both repos and services."""

from __future__ import annotations


class DuplicatePendingItemError(Exception):
    """Raised when a flush hits the dedup partial-unique index under concurrency."""

    def __init__(self) -> None:
        super().__init__("Concurrent duplicate pending item detected")
