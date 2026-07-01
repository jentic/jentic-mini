"""Argon2id password hashing and verification."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Single source of truth for the minimum password length. The Pydantic request
# schemas enforce this for the web path (Field(min_length=...)); the service
# layer re-checks it for the CLI path that bypasses the schema. Keep this in
# lockstep with the Go CLI's `minPasswordLen` and the UI's MIN_PASSWORD_LENGTH.
MIN_PASSWORD_LENGTH = 12
# Reused so every "too short" rejection reads identically across call sites.
PASSWORD_TOO_SHORT_MESSAGE = f"Password must be at least {MIN_PASSWORD_LENGTH} characters"

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    """Hash a plaintext password using argon2id."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an argon2id hash."""
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """Check if a hash needs to be re-hashed with updated parameters."""
    return _hasher.check_needs_rehash(hashed)
