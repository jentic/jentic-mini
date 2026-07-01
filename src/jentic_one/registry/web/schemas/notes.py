"""Request/response schemas for the Notes endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator


class NoteType(StrEnum):
    """Category of a note (matches the spec ``NoteType`` enum)."""

    auth_quirk = "auth_quirk"
    usage_hint = "usage_hint"
    execution_feedback = "execution_feedback"
    correction = "correction"


class NoteConfidence(StrEnum):
    """Author-supplied confidence in a note (matches the spec ``NoteConfidence`` enum)."""

    observed = "observed"
    suspected = "suspected"
    verified = "verified"


class NoteSource(StrEnum):
    """Origin tag for a note (matches the spec ``NoteSource`` enum)."""

    agent = "agent"
    human = "human"
    platform = "platform"


class NoteApiReference(BaseModel):
    """Loose ``(vendor, name, version)`` identity tuple for a registered API."""

    model_config = ConfigDict(extra="forbid")

    vendor: str
    name: str
    version: str


class NoteResource(BaseModel):
    """Exactly-one-of resource identifier for a note (request side)."""

    model_config = ConfigDict(extra="forbid")

    api: NoteApiReference | None = None
    operation_id: str | None = None
    execution_id: str | None = None
    credential_id: str | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> NoteResource:
        populated = sum(
            1
            for v in [self.api, self.operation_id, self.execution_id, self.credential_id]
            if v is not None
        )
        if populated != 1:
            msg = "Exactly one resource field must be provided"
            raise ValueError(msg)
        return self


class NoteCreateRequest(BaseModel):
    """Payload for creating a new note."""

    model_config = ConfigDict(extra="forbid")

    resource: NoteResource
    type: NoteType | None = None
    body: str = Field(max_length=4000)
    confidence: NoteConfidence | None = None
    source: NoteSource | None = None
    related_execution_id: str | None = None


class NoteUpdateRequest(BaseModel):
    """Payload for updating an existing note (partial)."""

    model_config = ConfigDict(extra="forbid")

    body: str | None = Field(default=None, max_length=4000)
    type: NoteType | None = None
    confidence: NoteConfidence | None = None
    source: NoteSource | None = None
    related_execution_id: str | None = None

    @model_validator(mode="after")
    def _body_not_null(self) -> NoteUpdateRequest:
        if "body" in self.model_fields_set and self.body is None:
            msg = "body may not be null"
            raise ValueError(msg)
        return self


class NoteResourceResponse(BaseModel):
    """Polymorphic reference to the resource a note is attached to (response side)."""

    api: NoteApiReference | None = None
    operation_id: str | None = None
    execution_id: str | None = None
    credential_id: str | None = None

    @model_serializer
    def _serialize(self) -> dict[str, Any]:
        """Emit only the single populated resource field, matching the spec shape."""
        if self.api is not None:
            return {"api": self.api.model_dump()}
        if self.operation_id is not None:
            return {"operation_id": self.operation_id}
        if self.execution_id is not None:
            return {"execution_id": self.execution_id}
        if self.credential_id is not None:
            return {"credential_id": self.credential_id}
        return {}


class NoteLinksResponse(BaseModel):
    """Hypermedia links for a note resource."""

    model_config = ConfigDict(populate_by_name=True)

    self_link: str = Field(serialization_alias="self")
    resource: str | None = None


class NoteResponse(BaseModel):
    """Full note resource response."""

    model_config = ConfigDict(populate_by_name=True)

    note_id: str
    resource: NoteResourceResponse
    type: NoteType | None
    body: str
    confidence: NoteConfidence | None
    confidence_source: str
    source: NoteSource | None
    created_by: str
    related_execution_id: str | None
    revision: int
    created_at: datetime
    updated_at: datetime
    links: NoteLinksResponse = Field(serialization_alias="_links")


class NoteListResponse(BaseModel):
    """Cursor-paginated list of notes."""

    data: list[NoteResponse]
    has_more: bool
    next_cursor: str | None = None
