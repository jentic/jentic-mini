"""Integration tests for UrlIndexRepository."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.core.schema.operation_url_index import OperationURLIndex
from jentic_one.registry.core.url_index import build_index_entry
from jentic_one.registry.repos.operation_repo import OperationInput, OperationRepository
from jentic_one.registry.repos.url_index_repo import UrlIndexRepository
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


async def test_upsert_entry_creates_row(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """upsert_entry creates a new URL index row."""
    _, rev = sample_revision
    ops = [OperationInput(path="/pets/{petId}", method="GET")]

    async with registry_db.session() as session:
        op_ids = await OperationRepository.bulk_create(session, rev.id, ops, created_by="usr_test")
        await session.commit()

    entry = build_index_entry("api.example.com", "/pets/{petId}", "https")

    async with registry_db.session() as session:
        await UrlIndexRepository.upsert_entry(
            session,
            revision_id=rev.id,
            operation_id=op_ids[0],
            method="GET",
            entry=entry,
            created_by="usr_test",
        )
        await session.commit()

    async with registry_db.session() as session:
        result = await session.execute(
            select(OperationURLIndex).where(OperationURLIndex.revision_id == rev.id)
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        row = rows[0]
        assert row.method == "GET"
        assert row.host == "api.example.com"
        assert row.path_template == "/pets/{petId}"
        assert row.operation_id == op_ids[0]
        assert row.segment_count == 2
        assert row.param_names == ["petId"]


async def test_upsert_entry_updates_on_conflict(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """upsert_entry with same natural key updates operation_id/revision_id."""
    _, rev = sample_revision
    ops = [
        OperationInput(path="/items/{id}", method="GET"),
        OperationInput(path="/items/{id}", method="PUT"),
    ]

    async with registry_db.session() as session:
        op_ids = await OperationRepository.bulk_create(session, rev.id, ops, created_by="usr_test")
        await session.commit()

    entry = build_index_entry("api.example.com", "/items/{id}", "https")

    async with registry_db.session() as session:
        await UrlIndexRepository.upsert_entry(
            session,
            revision_id=rev.id,
            operation_id=op_ids[0],
            method="GET",
            entry=entry,
            created_by="usr_test",
        )
        await session.commit()

    async with registry_db.session() as session:
        await UrlIndexRepository.upsert_entry(
            session,
            revision_id=rev.id,
            operation_id=op_ids[1],
            method="GET",
            entry=entry,
            created_by="usr_test",
        )
        await session.commit()

    async with registry_db.session() as session:
        result = await session.execute(
            select(OperationURLIndex).where(OperationURLIndex.revision_id == rev.id)
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].operation_id == op_ids[1]


async def test_delete_for_revision(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """delete_for_revision removes all index entries for the revision."""
    _, rev = sample_revision
    ops = [OperationInput(path="/x", method="GET")]

    async with registry_db.session() as session:
        op_ids = await OperationRepository.bulk_create(session, rev.id, ops, created_by="usr_test")
        await session.commit()

    entry = build_index_entry("host.com", "/x", "https")

    async with registry_db.session() as session:
        await UrlIndexRepository.upsert_entry(
            session,
            revision_id=rev.id,
            operation_id=op_ids[0],
            method="GET",
            entry=entry,
            created_by="usr_test",
        )
        await session.commit()

    async with registry_db.session() as session:
        await UrlIndexRepository.delete_for_revision(session, rev.id)
        await session.commit()

    async with registry_db.session() as session:
        result = await session.execute(
            select(OperationURLIndex).where(OperationURLIndex.revision_id == rev.id)
        )
        assert result.scalars().all() == []
