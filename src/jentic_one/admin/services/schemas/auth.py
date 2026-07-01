"""Authentication schemas.

These now live in :mod:`jentic_one.shared.auth.identity` so all surfaces share
the same identity primitives. Re-exported here for backwards compatibility.
"""

from __future__ import annotations

from jentic_one.shared.auth.identity import (
    ChangePasswordPayload,
    Identity,
    LoginPayload,
    TokenBundle,
)

__all__ = [
    "ChangePasswordPayload",
    "Identity",
    "LoginPayload",
    "TokenBundle",
]
