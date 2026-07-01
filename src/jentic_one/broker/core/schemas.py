"""Broker execute request/response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExecuteRequestContext(BaseModel):
    """Contextual metadata for a broker proxy request — discovery-driven.

    ``toolkit_id`` is no longer a required inbound header: it is derived (§03) or
    supplied as an inbound disambiguator. ``operation_id`` / ``api_*`` come from
    in-process discovery, not inbound ``Jentic-Api-*`` headers.
    """

    upstream_url: str
    method: str
    trace_id: str
    toolkit_id: str | None = None
    operation_id: str | None = None
    api_vendor: str | None = None
    api_name: str | None = None
    api_version: str | None = None
    prefer: str | None = None
    pinned_revisions: dict[str, Any] | None = None


class AsyncQueuedResponseLinks(BaseModel):
    """HAL-style links for the async response."""

    self_link: str = Field(serialization_alias="self")


class AsyncQueuedResponse(BaseModel):
    """Response body for 202 async-queued executions."""

    job_id: str
    links: AsyncQueuedResponseLinks = Field(serialization_alias="_links")
