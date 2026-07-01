"""Request/response schemas for the search endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from jentic_one.registry.web.schemas.apis import ApiReferenceResponse


class SearchRequest(BaseModel):
    """POST /search request body."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    apis: list[str] | None = None
    limit: int = Field(default=10, ge=1, le=100)
    cursor: str | None = None
    revision_pins: dict[str, str] | None = None


class SearchLinksResponse(BaseModel):
    """Hypermedia links for a search result row."""

    inspect: str


class OperationResultResponse(BaseModel):
    """A single search result matching the OperationResult spec."""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["operation"] = "operation"
    api: ApiReferenceResponse
    operation_id: str
    method: str
    url: str
    name: str | None = None
    description: str | None = None
    relevance_score: float
    links: SearchLinksResponse = Field(serialization_alias="_links")


class SearchResponse(BaseModel):
    """Cursor-paginated search results page."""

    data: list[OperationResultResponse]
    has_more: bool
    next_cursor: str | None = None
