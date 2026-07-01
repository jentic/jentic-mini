"""Shared Accept-header content negotiation utilities."""

from __future__ import annotations

import contextlib

from fastapi import Request


def accepted_media_types(request: Request) -> list[str]:
    """Parse Accept header into ordered list of media types (highest q first)."""
    accept_header = request.headers.get("accept", "application/json")
    types: list[tuple[float, str]] = []
    for part in accept_header.split(","):
        part = part.strip()
        if not part:
            continue
        params = part.split(";")
        media_type = params[0].strip()
        q = 1.0
        for param in params[1:]:
            param = param.strip()
            if param.startswith("q="):
                with contextlib.suppress(ValueError):
                    q = float(param[2:])
        types.append((q, media_type))
    types.sort(key=lambda t: -t[0])
    return [t[1] for t in types]
