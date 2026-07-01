"""User schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EffectivePermissionView(BaseModel):
    """A single effective permission with provenance."""

    name: str
    implied_by: str | None = None


class UserView(BaseModel):
    """Public user representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    first_name: str
    last_name: str
    name: str
    active: bool
    auth_provider: str
    invite_state: str
    must_change_password: bool
    external_subject_id: str | None = None
    assigned: list[str] = []
    effective: list[EffectivePermissionView] = []
    created_at: datetime
    updated_at: datetime | None = None


class UserCreatePayload(BaseModel):
    """Payload for creating a new user."""

    email: str
    first_name: str
    last_name: str
    permissions: list[str] = []


class UserUpdatePayload(BaseModel):
    """Payload for updating a user."""

    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class UserCreatedView(BaseModel):
    """Response after user creation including invite token."""

    user: UserView
    invite_token: str
    invite_expires_at: datetime
