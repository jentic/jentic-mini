"""JWT issue/verify primitives shared across surfaces."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt


def issue_jwt(claims: dict[str, Any], secret: str, ttl_seconds: int) -> str:
    """Sign a JWT with HS256 containing the given claims and expiry."""
    now = datetime.now(UTC)
    payload = {
        **claims,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_jwt(token: str, secret: str) -> dict[str, Any]:
    """Verify and decode a JWT. Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError."""
    result: dict[str, Any] = jwt.decode(token, secret, algorithms=["HS256"])
    return result
