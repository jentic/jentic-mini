"""Tests for toolkit agent response Pydantic schema validation."""

from __future__ import annotations

from datetime import UTC, datetime

from jentic_one.control.web.schemas.toolkits import (
    ToolkitAgentListResponse,
    ToolkitAgentResponse,
)


def test_toolkit_agent_response_round_trip() -> None:
    now = datetime.now(UTC)
    resp = ToolkitAgentResponse(
        agent_id="agt_abc123",
        agent_name="My Agent",
        status="active",
        bound_at=now,
    )
    data = resp.model_dump()
    assert data["agent_id"] == "agt_abc123"
    assert data["agent_name"] == "My Agent"
    assert data["status"] == "active"
    assert data["bound_at"] == now


def test_toolkit_agent_list_response_empty() -> None:
    resp = ToolkitAgentListResponse(data=[], has_more=False, next_cursor=None)
    data = resp.model_dump()
    assert data["data"] == []
    assert data["has_more"] is False
    assert data["next_cursor"] is None


def test_toolkit_agent_list_response_with_data() -> None:
    now = datetime.now(UTC)
    agents = [
        ToolkitAgentResponse(
            agent_id=f"agt_{i}",
            agent_name=f"Agent {i}",
            status="active",
            bound_at=now,
        )
        for i in range(3)
    ]
    resp = ToolkitAgentListResponse(
        data=agents,
        has_more=True,
        next_cursor="eyJ0IjogIjIwMjQtMDEtMDFUMDA6MDA6MDAiLCAiaWQiOiAiYXRiX3h5eiJ9",
    )
    data = resp.model_dump()
    assert len(data["data"]) == 3
    assert data["has_more"] is True
    assert data["next_cursor"] is not None


def test_toolkit_agent_list_response_null_cursor() -> None:
    resp = ToolkitAgentListResponse(data=[], has_more=False)
    assert resp.next_cursor is None
