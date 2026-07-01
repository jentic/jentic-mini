"""Integration tests for JobRepository against real PostgreSQL."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete

from jentic_one.admin.core.schema.jobs import Job
from jentic_one.admin.repos import JobRepository
from jentic_one.shared.db.session import DatabaseSession
from jentic_one.shared.models import JobKind, JobStatus

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_jobs(admin_db: DatabaseSession) -> AsyncGenerator[None, None]:
    """Ensure the ``jobs`` table is empty before and after each test."""
    async with admin_db.session() as session:
        await session.execute(delete(Job))
        await session.commit()
    yield
    async with admin_db.session() as session:
        await session.execute(delete(Job))
        await session.commit()


async def test_create_and_get_round_trip(admin_db: DatabaseSession, clean_jobs: None) -> None:
    """create() persists a Job that get_by_id() can retrieve with all fields."""
    async with admin_db.session() as session:
        job = await JobRepository.create(
            session,
            kind=JobKind.EXECUTION,
            status=JobStatus.QUEUED,
            execution_id="exec_abc123",
            created_by="usr_test",
        )
        await session.commit()
        job_id = job.id

    async with admin_db.session() as session:
        loaded = await JobRepository.get_by_id(session, job_id)
        assert loaded is not None
        assert loaded.id == job_id
        assert loaded.kind == JobKind.EXECUTION
        assert loaded.status == JobStatus.QUEUED
        assert loaded.execution_id == "exec_abc123"
        assert loaded.error is None
        assert loaded.parent_job_id is None


async def test_update_write_or_keep_semantics(admin_db: DatabaseSession, clean_jobs: None) -> None:
    """update() with error=None does not clear an existing error value."""
    async with admin_db.session() as session:
        job = await JobRepository.create(session, kind=JobKind.IMPORT, created_by="usr_test")
        await session.commit()
        job_id = job.id

    async with admin_db.session() as session:
        await JobRepository.update(session, job_id, error="something broke")
        await session.commit()

    async with admin_db.session() as session:
        await JobRepository.update(session, job_id, error=None)
        await session.commit()

    async with admin_db.session() as session:
        loaded = await JobRepository.get_by_id(session, job_id)
        assert loaded is not None
        assert loaded.error == "something broke"


async def test_get_child_job_ids(admin_db: DatabaseSession, clean_jobs: None) -> None:
    """get_child_job_ids() returns child IDs ordered by created_at."""
    async with admin_db.session() as session:
        parent = await JobRepository.create(session, kind=JobKind.IMPORT, created_by="usr_test")
        await session.flush()
        child1 = await JobRepository.create(
            session,
            kind=JobKind.EXECUTION,
            parent_job_id=parent.id,
            created_by="usr_test",
        )
        await session.flush()
        child2 = await JobRepository.create(
            session,
            kind=JobKind.EXECUTION,
            parent_job_id=parent.id,
            created_by="usr_test",
        )
        await session.commit()

        parent_id = parent.id
        child1_id = child1.id
        child2_id = child2.id

    async with admin_db.session() as session:
        ids = await JobRepository.get_child_job_ids(session, parent_id)
        assert ids == [child1_id, child2_id]


async def test_get_child_status_counts(admin_db: DatabaseSession, clean_jobs: None) -> None:
    """get_child_status_counts() returns a dict mapping status to count."""
    async with admin_db.session() as session:
        parent = await JobRepository.create(session, kind=JobKind.IMPORT, created_by="usr_test")
        await session.flush()
        await JobRepository.create(
            session,
            kind=JobKind.EXECUTION,
            status=JobStatus.RUNNING,
            parent_job_id=parent.id,
            created_by="usr_test",
        )
        await JobRepository.create(
            session,
            kind=JobKind.EXECUTION,
            status=JobStatus.RUNNING,
            parent_job_id=parent.id,
            created_by="usr_test",
        )
        await JobRepository.create(
            session,
            kind=JobKind.EXECUTION,
            status=JobStatus.COMPLETED,
            parent_job_id=parent.id,
            created_by="usr_test",
        )
        await session.commit()
        parent_id = parent.id

    async with admin_db.session() as session:
        counts = await JobRepository.get_child_status_counts(session, parent_id)
        assert counts == {JobStatus.RUNNING: 2, JobStatus.COMPLETED: 1}
