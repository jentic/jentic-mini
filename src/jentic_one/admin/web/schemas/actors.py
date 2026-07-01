"""Actor API response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from jentic_one.shared.models import ActorType


class ActorSummaryResponse(BaseModel):
    """Single actor entry in the actors list."""

    id: str
    actor_type: ActorType
    name: str
    active: bool
    created_at: datetime


class ActorListResponse(BaseModel):
    """Paginated list of actors."""

    data: list[ActorSummaryResponse]
    has_more: bool
    next_cursor: str | None = None
