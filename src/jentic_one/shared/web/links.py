"""Shared link-builder utility for consistent absolute URLs in API responses."""

from __future__ import annotations

from starlette.requests import Request


def build_link(request: Request, path: str) -> str:
    """Return an absolute URL for the given path rooted at the request's base URL."""
    return str(request.base_url).rstrip("/") + "/" + path.lstrip("/")
