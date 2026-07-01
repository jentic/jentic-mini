"""Actor summary schemas for the unified actors endpoint."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from jentic_one.shared.models import ActorType


class ActorView(BaseModel):
    """Lightweight actor representation for UI cache hydration."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_type: ActorType
    name: str
    active: bool
    created_at: datetime
