"""Unit tests for the monitoring router response schema."""

from __future__ import annotations

from jentic_one.admin.web.schemas.monitoring import (
    DailyExecutionBucket,
    ExecutionStatsResponse,
    TopOperation,
)


def test_execution_stats_response_serializes() -> None:
    resp = ExecutionStatsResponse(
        total_executions=100,
        success_rate_percent=92.5,
        daily_buckets=[
            DailyExecutionBucket(date="2026-06-20", total=50, success=46, failed=4),
            DailyExecutionBucket(date="2026-06-21", total=50, success=47, failed=3),
        ],
        top_operations=[
            TopOperation(
                api_vendor="stripe",
                api_name="payments",
                operation_id="createCharge",
                total=30,
                failed=1,
            ),
        ],
    )
    data = resp.model_dump()
    assert data["total_executions"] == 100
    assert data["success_rate_percent"] == 92.5
    assert len(data["daily_buckets"]) == 2
    assert data["daily_buckets"][0]["date"] == "2026-06-20"
    assert len(data["top_operations"]) == 1
    assert data["top_operations"][0]["operation_id"] == "createCharge"


def test_empty_response() -> None:
    resp = ExecutionStatsResponse(
        total_executions=0,
        success_rate_percent=0.0,
        daily_buckets=[],
        top_operations=[],
    )
    data = resp.model_dump()
    assert data["total_executions"] == 0
    assert data["daily_buckets"] == []
    assert data["top_operations"] == []
