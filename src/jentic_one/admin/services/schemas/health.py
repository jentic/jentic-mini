"""Health check schemas."""

from __future__ import annotations

from pydantic import BaseModel


class HealthView(BaseModel):
    """Health check response."""

    status: str = "ok"
    surface: str = "admin"
    setup_required: bool = False
    next_step: str | None = None
