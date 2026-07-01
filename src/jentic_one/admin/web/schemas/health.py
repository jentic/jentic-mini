"""Health response schema."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response for the admin surface."""

    status: str
    surface: str
    setup_required: bool
    next_step: str | None = None
