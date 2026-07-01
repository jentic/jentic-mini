"""Broker execution domain helpers (pure — no transport/DB)."""

from __future__ import annotations

import uuid


def mint_execution_id() -> str:
    """Generate a unique execution ID with the exec_ prefix."""
    return f"exec_{uuid.uuid4().hex[:24]}"
