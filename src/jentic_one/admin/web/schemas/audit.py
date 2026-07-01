"""Audit entry request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditResponse(BaseModel):
    """Audit entry representation in API responses."""

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


class AuditListResponse(BaseModel):
    """Paginated list of audit entries."""

    data: list[AuditResponse]
    has_more: bool
    next_cursor: str | None = None
