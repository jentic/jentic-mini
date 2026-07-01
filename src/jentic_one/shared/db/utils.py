"""Shared database utility functions."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """UTC-aware now() for app-side timestamp defaults (microsecond resolution)."""
    return datetime.now(UTC)
