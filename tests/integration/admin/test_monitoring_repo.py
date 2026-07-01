"""Integration tests for MonitoringRepository aggregations on both backends.

These run under ``make test-integration`` (PostgreSQL) and
``make test-integration-sqlite`` (SQLite). The ``daily_buckets`` query used to
hard-code the Postgres-only ``date_trunc`` function, which 500'd the
``GET /monitoring/executions`` endpoint on SQLite (issue #623); these tests
guard the portable, dialect-aware day-bucket expression.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from jentic_one.admin.core.schema.execution_records import ExecutionRecord
from jentic_one.admin.repos import ExecutionRecordRepository
from jentic_one.admin.repos.monitoring_repo import MonitoringRepository
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_execution_records(admin_db: DatabaseSession) -> AsyncGenerator[None, None]:
    async with admin_db.session() as session:
        await session.execute(delete(ExecutionRecord))
        await session.commit()
    yield
    async with admin_db.session() as session:
        await session.execute(delete(ExecutionRecord))
        await session.commit()


async def _seed(
    admin_db: DatabaseSession, started_at: datetime, status: str, **kwargs: object
) -> None:
    async with admin_db.session() as session:
        await ExecutionRecordRepository.create(
            session,
            toolkit_id="tk_test000000000000000000",
            trace_id="abcdef1234567890abcdef12",
            started_at=started_at,
            status=status,
            created_by="usr_test",
            actor_id="usr_test",
            actor_type="user",
            **kwargs,  # type: ignore[arg-type]
        )
        await session.commit()


async def test_daily_buckets_groups_by_day(
    admin_db: DatabaseSession, clean_execution_records: None
) -> None:
    now = datetime.now(UTC)
    # Two executions today, one yesterday — must collapse into two day buckets.
    await _seed(admin_db, now, "completed")
    await _seed(admin_db, now - timedelta(minutes=30), "failed")
    await _seed(admin_db, now - timedelta(days=1), "completed")

    cutoff = now - timedelta(days=7)
    async with admin_db.session() as session:
        buckets = await MonitoringRepository.daily_buckets(session, cutoff)

    assert len(buckets) == 2
    # Each bucket date is a YYYY-MM-DD string on both backends.
    for bucket in buckets:
        assert len(bucket.date) == 10
        assert bucket.date[4] == "-" and bucket.date[7] == "-"
    by_date = {b.date: b for b in buckets}
    today = by_date[now.strftime("%Y-%m-%d")]
    assert today.total == 2
    assert today.success == 1
    assert today.failed == 1


async def test_daily_buckets_respects_cutoff(
    admin_db: DatabaseSession, clean_execution_records: None
) -> None:
    now = datetime.now(UTC)
    await _seed(admin_db, now, "completed")
    await _seed(admin_db, now - timedelta(days=10), "completed")  # before cutoff

    async with admin_db.session() as session:
        buckets = await MonitoringRepository.daily_buckets(session, now - timedelta(days=7))

    assert len(buckets) == 1
    assert buckets[0].total == 1


async def test_daily_buckets_empty(
    admin_db: DatabaseSession, clean_execution_records: None
) -> None:
    async with admin_db.session() as session:
        buckets = await MonitoringRepository.daily_buckets(
            session, datetime.now(UTC) - timedelta(days=7)
        )
    assert buckets == []


async def test_top_operations_ranks_by_total(
    admin_db: DatabaseSession, clean_execution_records: None
) -> None:
    now = datetime.now(UTC)
    for _ in range(3):
        await _seed(
            admin_db,
            now,
            "completed",
            operation_id="listUsers",
            api_vendor="github",
            api_name="rest",
        )
    await _seed(
        admin_db,
        now,
        "failed",
        operation_id="getRepo",
        api_vendor="github",
        api_name="rest",
    )

    async with admin_db.session() as session:
        ops = await MonitoringRepository.top_operations(session, now - timedelta(days=7))

    assert ops[0].operation_id == "listUsers"
    assert ops[0].total == 3
    failed_op = next(o for o in ops if o.operation_id == "getRepo")
    assert failed_op.failed == 1
