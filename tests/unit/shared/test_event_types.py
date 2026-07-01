"""Unit tests for EventType constants."""

from jentic_one.shared.models.events import EventType


def test_new_event_types_in_all() -> None:
    """All three new event types must appear in EventType.ALL."""
    assert EventType.UPSTREAM_CIRCUIT_OPEN in EventType.ALL
    assert EventType.JOB_FAILED_PERMANENTLY in EventType.ALL
    assert EventType.UNAUTHORIZED_ACCESS_ATTEMPT in EventType.ALL


def test_event_type_values() -> None:
    """Event type string values match the namespaced convention."""
    assert EventType.UPSTREAM_CIRCUIT_OPEN == "upstream.circuit_open"
    assert EventType.JOB_FAILED_PERMANENTLY == "job.failed_permanently"
    assert EventType.UNAUTHORIZED_ACCESS_ATTEMPT == "security.unauthorized_access_attempt"


def test_all_contains_every_class_constant() -> None:
    """Every string constant on EventType must be in ALL (no drift)."""
    constants = {v for k, v in vars(EventType).items() if not k.startswith("_") and k != "ALL"}
    assert constants == EventType.ALL
