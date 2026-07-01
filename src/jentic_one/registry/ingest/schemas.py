"""Ingest result schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from jentic_one.shared.models import ApiRevisionState


class IngestResult(BaseModel):
    """Result of a successful ingest operation."""

    api_vendor: str
    api_name: str
    api_version: str
    revision_id: uuid.UUID
    state: ApiRevisionState = ApiRevisionState.DRAFT
    operation_count: int
