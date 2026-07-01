"""Admin service metrics — counters for auth outcomes and audit events."""

from __future__ import annotations

from jentic_one.shared.audit import audit_events_counter
from jentic_one.shared.metrics import get_meter

_meter = get_meter("admin")

login_counter = _meter.create_counter(
    "admin.auth.login",
    description="Login attempts by outcome",
)

__all__ = ["audit_events_counter", "login_counter"]
