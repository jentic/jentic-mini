"""Errors for the search capability."""

from __future__ import annotations


class SearchUnsupportedError(RuntimeError):
    """Raised when the active database backend cannot satisfy the requested search."""
