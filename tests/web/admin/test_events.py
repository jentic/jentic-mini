"""Web tests for the admin events router."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import cast

import pytest
from fastapi.testclient import TestClient

from jentic_one.admin.services.event_stream_service import EventStreamService
from jentic_one.admin.services.schemas.events import EventView, Heartbeat
from jentic_one.shared.context import Context

pytestmark = pytest.mark.integration


def test_list_success(authed_client: TestClient) -> None:
    resp = authed_client.get("/events")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "has_more" in data


def test_list_with_filters(authed_client: TestClient) -> None:
    resp = authed_client.get("/events?severity=warning&requires_action=false")
    assert resp.status_code == 200


def test_list_without_auth(unauthed_client: TestClient) -> None:
    resp = unauthed_client.get("/events")
    assert resp.status_code == 401


def test_get_not_found(authed_client: TestClient) -> None:
    resp = authed_client.get("/events/nonexistent-event-id")
    assert resp.status_code == 404
    assert resp.json()["type"] == "event_not_found"


async def test_stream_yields_heartbeat_when_idle(web_context: Context) -> None:
    # The SSE endpoint streams forever, which a blocking HTTP TestClient cannot
    # drive without hanging. Exercise the streaming source directly instead:
    # with no events, the first item must be a heartbeat. A short poll interval
    # keeps the test fast and we stop after the first item.
    svc = EventStreamService(web_context)
    stream = cast(
        "AsyncGenerator[EventView | Heartbeat, None]",
        svc.stream(poll_interval_seconds=0.01),
    )
    try:
        first = await stream.__anext__()
    finally:
        await stream.aclose()
    assert isinstance(first, Heartbeat)
