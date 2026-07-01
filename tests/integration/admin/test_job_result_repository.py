"""Integration tests for JobResultRepository against real PostgreSQL."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from jentic_one.admin.core.schema.job_results import JobResult
from jentic_one.admin.core.schema.jobs import Job
from jentic_one.admin.repos import JobRepository, JobResultRepository
from jentic_one.shared.db.session import DatabaseSession
from jentic_one.shared.models import JobKind

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_job_results(admin_db: DatabaseSession) -> AsyncGenerator[None, None]:
    async with admin_db.session() as session:
        await session.execute(delete(JobResult))
        await session.execute(delete(Job))
        await session.commit()
    yield
    async with admin_db.session() as session:
        await session.execute(delete(JobResult))
        await session.execute(delete(Job))
        await session.commit()


@pytest.fixture()
async def test_job(admin_db: DatabaseSession, clean_job_results: None) -> str:
    async with admin_db.session() as session:
        job = await JobRepository.create(session, kind=JobKind.EXECUTION, created_by="usr_test")
        await session.commit()
        return job.id


async def test_create_generates_ksuid(admin_db: DatabaseSession, test_job: str) -> None:
    async with admin_db.session() as session:
        result = await JobResultRepository.create(
            session,
            job_id=test_job,
            kind="execution",
            body={"output": "success"},
            created_by="usr_test",
        )
        await session.commit()
        assert result.id.startswith("jres_")
        assert len(result.id) == 29


async def test_create_and_get_by_job_id(admin_db: DatabaseSession, test_job: str) -> None:
    async with admin_db.session() as session:
        await JobResultRepository.create(
            session,
            job_id=test_job,
            kind="execution",
            body={"data": [1, 2, 3]},
            available_until=datetime.now(UTC) + timedelta(days=7),
            created_by="usr_test",
        )
        await session.commit()

    async with admin_db.session() as session:
        loaded = await JobResultRepository.get_by_job_id(session, test_job)
        assert loaded is not None
        assert loaded.kind == "execution"
        assert loaded.body == {"data": [1, 2, 3]}
        assert loaded.available_until is not None


async def test_get_by_job_id_not_found(admin_db: DatabaseSession, clean_job_results: None) -> None:
    async with admin_db.session() as session:
        result = await JobResultRepository.get_by_job_id(session, "job_nonexistent0000000000")
        assert result is None


async def test_delete_expired(admin_db: DatabaseSession, clean_job_results: None) -> None:
    async with admin_db.session() as session:
        job1 = await JobRepository.create(session, kind=JobKind.EXECUTION, created_by="usr_test")
        job2 = await JobRepository.create(session, kind=JobKind.EXECUTION, created_by="usr_test")
        job3 = await JobRepository.create(session, kind=JobKind.EXECUTION, created_by="usr_test")
        await session.flush()

        await JobResultRepository.create(
            session,
            job_id=job1.id,
            kind="execution",
            body={},
            available_until=datetime.now(UTC) - timedelta(hours=1),
            created_by="usr_test",
        )
        await JobResultRepository.create(
            session,
            job_id=job2.id,
            kind="execution",
            body={},
            available_until=datetime.now(UTC) + timedelta(hours=1),
            created_by="usr_test",
        )
        await JobResultRepository.create(
            session,
            job_id=job3.id,
            kind="execution",
            body={},
            available_until=None,
            created_by="usr_test",
        )
        await session.commit()

    async with admin_db.session() as session:
        deleted_count = await JobResultRepository.delete_expired(session)
        await session.commit()
        assert deleted_count == 1

    async with admin_db.session() as session:
        remaining1 = await JobResultRepository.get_by_job_id(session, job2.id)
        remaining2 = await JobResultRepository.get_by_job_id(session, job3.id)
        assert remaining1 is not None
        assert remaining2 is not None
        gone = await JobResultRepository.get_by_job_id(session, job1.id)
        assert gone is None
