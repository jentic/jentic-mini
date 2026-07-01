"""Unit tests for execution response serialization and actor fields."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from jentic_one.admin.services.schemas.executions import ExecutionView
from jentic_one.admin.web.routers.executions import _execution_response


def _make_request() -> MagicMock:
    request = MagicMock()
    request.base_url = "http://testserver/"
    return request


def _make_execution_view(**overrides: object) -> ExecutionView:
    defaults: dict[str, object] = {
        "id": "exec_001",
        "toolkit_id": "tk_test000000000000000000",
        "trace_id": "a" * 32,
        "started_at": datetime(2026, 6, 1, tzinfo=UTC),
        "duration_ms": 150,
        "status": "completed",
        "operation_id": "getThing",
        "api": None,
        "pinned_revisions": None,
        "http_status": 200,
        "error": None,
        "created_at": datetime(2026, 6, 1, tzinfo=UTC),
        "actor_id": "usr_test",
        "actor_type": "user",
    }
    defaults.update(overrides)
    return ExecutionView(**defaults)  # type: ignore[arg-type]


def test_actor_fields_present_in_response() -> None:
    view = _make_execution_view(actor_id="agt_abc", actor_type="agent")
    request = _make_request()
    resp = _execution_response(view, request)
    data = resp.model_dump(by_alias=True)
    assert data["actor_id"] == "agt_abc"
    assert data["actor_type"] == "agent"


def test_actor_fields_always_present() -> None:
    view = _make_execution_view(actor_id="usr_xyz", actor_type="user")
    request = _make_request()
    resp = _execution_response(view, request)
    data = resp.model_dump(by_alias=True)
    assert data["actor_id"] == "usr_xyz"
    assert data["actor_type"] == "user"


def test_response_includes_standard_fields() -> None:
    view = _make_execution_view(actor_id="usr_xyz", actor_type="user")
    request = _make_request()
    resp = _execution_response(view, request)
    data = resp.model_dump(by_alias=True)
    assert data["execution_id"] == "exec_001"
    assert data["toolkit_id"] == "tk_test000000000000000000"
    assert data["status"] == "completed"
    assert data["_links"]["self"] == "http://testserver/executions/exec_001"
