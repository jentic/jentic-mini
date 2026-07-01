"""Service-layer views for provider config management."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProviderConfigView(BaseModel):
    """A redacted view of a stored provider config returned by the service."""

    name: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None = None
