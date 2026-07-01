"""Invite token schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class InviteIssued(BaseModel):
    """Response containing the plaintext invite token (shown once)."""

    token: str
    expires_at: datetime


class RedeemPayload(BaseModel):
    """Payload for redeeming an invite token."""

    token: str
    new_password: str
