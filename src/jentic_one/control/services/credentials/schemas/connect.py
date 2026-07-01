"""Connect-flow value objects for the credential provider protocol."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ConnectRequest(BaseModel):
    """Inbound connect intent from the caller."""

    scopes: list[str] = Field(default_factory=list)
    extra: dict[str, str] = Field(default_factory=dict)


class ConnectChallenge(BaseModel):
    """Outbound challenge returned by a provider's begin_connect."""

    authorize_url: str
    state: str


class ConnectState(BaseModel):
    """Verified, decoded state payload from the connect flow."""

    credential_id: str
    provider: str
    actor_id: str | None = None
    actor_type: str | None = None
    issued_at: datetime
    nonce: str


class ConnectCallback(BaseModel):
    """Provider-agnostic callback inputs received after user authorization."""

    code: str | None = None
    account_id: str | None = None
    error: str | None = None
    raw: dict[str, str] = Field(default_factory=dict)
