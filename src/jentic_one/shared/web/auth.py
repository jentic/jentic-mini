"""Shared HTTP auth helpers for FastAPI surfaces."""

from __future__ import annotations

from fastapi import Request
from jentic.problem_details import Unauthorized

API_KEY_HEADER = "x-jentic-api-key"


def extract_credential(request: Request) -> str:
    """Extract a credential from the request: API key header first, then Bearer token.

    Returns the raw credential string. Raises ``Unauthorized`` if neither is present.
    """
    api_key = request.headers.get(API_KEY_HEADER)
    if api_key:
        return api_key

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ")

    raise Unauthorized(
        detail="Authentication required",
        instance=request.url.path,
        type="unauthorized",
    )


def extract_bearer_token(request: Request) -> str:
    """Extract the Bearer token from the Authorization header.

    Raises the standard RFC-9457 ``Unauthorized`` problem when the header is
    missing or malformed. Performs no signature verification.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise Unauthorized(
            detail="Authentication required",
            instance=request.url.path,
            type="unauthorized",
        )
    return auth_header.removeprefix("Bearer ")
