"""User-related enums shared across modules."""

from enum import StrEnum


class InviteState(StrEnum):
    """State of a user invitation."""

    PENDING = "pending"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    ACCEPTED = "accepted"


class AuthProvider(StrEnum):
    """Authentication provider type."""

    LOCAL = "local"
    EXTERNAL = "external"
