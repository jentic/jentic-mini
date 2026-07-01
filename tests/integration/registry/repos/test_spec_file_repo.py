"""Integration tests for SpecFileRepository."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.core.schema.spec_files import SpecFile
from jentic_one.registry.repos.spec_file_repo import SpecFileRepository
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


async def test_create_or_update_creates(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """create_or_update creates a new SpecFile when none exists."""
    _, rev = sample_revision
    content = {"openapi": "3.1.0", "info": {"title": "Test", "version": "1.0"}}

    async with registry_db.session() as session:
        spec = await SpecFileRepository.create_or_update(
            session,
            revision_id=rev.id,
            filename="openapi.json",
            content=content,
            sha="abc123",
            source_id="src-001",
            created_by="usr_test",
        )
        await session.commit()

    assert spec.id is not None
    assert spec.filename == "openapi.json"
    assert spec.content == content
    assert spec.sha == "abc123"
    assert spec.source_id == "src-001"


async def test_create_or_update_updates(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """create_or_update updates content/sha on second call with same filename."""
    _, rev = sample_revision
    content_v1 = {"version": "1"}
    content_v2 = {"version": "2"}

    async with registry_db.session() as session:
        spec = await SpecFileRepository.create_or_update(
            session,
            revision_id=rev.id,
            filename="spec.yaml",
            content=content_v1,
            sha="sha1",
            created_by="usr_test",
        )
        await session.commit()
        spec_id = spec.id

    async with registry_db.session() as session:
        spec = await SpecFileRepository.create_or_update(
            session,
            revision_id=rev.id,
            filename="spec.yaml",
            content=content_v2,
            sha="sha2",
            source_id="new-source",
            created_by="usr_test",
        )
        await session.commit()

    assert spec.id == spec_id
    assert spec.content == content_v2
    assert spec.sha == "sha2"
    assert spec.source_id == "new-source"


async def test_revision_filename_uniqueness(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """(revision_id, filename) uniqueness is enforced at DB level.

    Note: create_or_update handles this via upsert logic, but direct
    inserts would fail.
    """
    _, rev = sample_revision

    async with registry_db.session() as session:
        sf1 = SpecFile(revision_id=rev.id, filename="dup.json", content={"a": 1})
        session.add(sf1)
        await session.commit()

    with pytest.raises(IntegrityError):
        async with registry_db.session() as session:
            sf2 = SpecFile(revision_id=rev.id, filename="dup.json", content={"b": 2})
            session.add(sf2)
            await session.commit()
