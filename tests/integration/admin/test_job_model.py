"""Integration tests for the Job ORM model against real PostgreSQL."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from jentic_one.admin.core.schema.jobs import Job
from jentic_one.shared.db.session import DatabaseSession
from jentic_one.shared.models import JobKind, JobStatus

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_jobs(admin_db: DatabaseSession) -> AsyncGenerator[None, None]:
    """Ensure the ``jobs`` table is empty before and after each test.

    The schema is migration-managed and shared across tests, so we clean rows
    rather than dropping the table.
    """
    async with admin_db.session() as session:
        await session.execute(delete(Job))
        await session.commit()
    yield
    async with admin_db.session() as session:
        await session.execute(delete(Job))
        await session.commit()


async def test_job_round_trip(admin_db: DatabaseSession, clean_jobs: None) -> None:
    """A Job can be inserted and read back with all fields intact."""
    job = Job(
        kind=JobKind.EXECUTION,
        status=JobStatus.QUEUED,
    )

    async with admin_db.session() as session:
        session.add(job)
        await session.commit()
        job_id = job.id

    async with admin_db.session() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        loaded = result.scalar_one()

        assert loaded.id == job_id
        assert loaded.kind == JobKind.EXECUTION
        assert loaded.status == JobStatus.QUEUED
        assert loaded.error is None
        assert loaded.execution_id is None
        assert loaded.created_at is not None
        assert loaded.parent_job_id is None


async def test_job_parent_child_relationship(admin_db: DatabaseSession, clean_jobs: None) -> None:
    """Parent/child self-referential relationship works correctly."""
    parent = Job(
        kind=JobKind.IMPORT,
        status=JobStatus.RUNNING,
    )

    async with admin_db.session() as session:
        session.add(parent)
        await session.commit()
        parent_id = parent.id

    child = Job(
        kind=JobKind.EXECUTION,
        status=JobStatus.QUEUED,
        parent_job_id=parent_id,
    )

    async with admin_db.session() as session:
        session.add(child)
        await session.commit()
        child_id = child.id

    async with admin_db.session() as session:
        result = await session.execute(
            select(Job).where(Job.id == child_id).options(selectinload(Job.parent))
        )
        loaded_child = result.scalar_one()
        assert loaded_child.parent_job_id == parent_id
        assert loaded_child.parent is not None
        assert loaded_child.parent.id == parent_id

        result = await session.execute(
            select(Job).where(Job.id == parent_id).options(selectinload(Job.children))
        )
        loaded_parent = result.scalar_one()
        assert len(loaded_parent.children) == 1
        assert loaded_parent.children[0].id == child_id
