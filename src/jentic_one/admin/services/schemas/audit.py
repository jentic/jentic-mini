"""Audit query schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from jentic_one.shared.models.audit import AuditTargetType


class AuditFilter(BaseModel):
    """Filter parameters for listing audit entries."""

    target_type: AuditTargetType | None = None
    target_id: str | None = None
    actor_id: str | None = None
    origin: str | None = None
    since: datetime | None = None
    until: datetime | None = None


class AuditView(BaseModel):
    """Public audit entry representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    occurred_at: datetime
    action: str
    target_type: str
    target_id: str
    target_parent_id: str | None = None
    actor_type: str
    actor_id: str | None = None
    actor_session_id: str | None = None
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    diff: dict[str, Any] | None = None
    request_id: str | None = None
    trace_id: str | None = None
    job_id: str | None = None
    reason: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    origin: str | None = None
