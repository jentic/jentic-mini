"""Integration tests for the SpecFile ORM model."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.core.schema.spec_files import SpecFile
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


async def test_spec_file_round_trip(registry_db: DatabaseSession, clean_registry: None) -> None:
    """SpecFile stores JSONB content and enforces unique (revision_id, filename)."""
    api = Api(vendor="petstore.io", name="pets", version="v1")

    async with registry_db.session() as session:
        session.add(api)
        await session.commit()
        api_id = api.id

    rev = ApiRevision(api_id=api_id)

    async with registry_db.session() as session:
        session.add(rev)
        await session.commit()
        rev_id = rev.id

    spec_content = {"openapi": "3.1.0", "info": {"title": "Petstore"}}
    sf = SpecFile(
        revision_id=rev_id,
        filename="openapi.yaml",
        content=spec_content,
        sha="abcdef1234567890",
        source_id="github:123",
    )

    async with registry_db.session() as session:
        session.add(sf)
        await session.commit()
        sf_id = sf.id

    async with registry_db.session() as session:
        result = await session.execute(select(SpecFile).where(SpecFile.id == sf_id))
        loaded = result.scalar_one()

        assert loaded.revision_id == rev_id
        assert loaded.filename == "openapi.yaml"
        assert loaded.content == spec_content
        assert loaded.sha == "abcdef1234567890"
        assert loaded.source_id == "github:123"
        assert loaded.created_at is not None

    # Duplicate filename for same revision should fail
    sf_dup = SpecFile(revision_id=rev_id, filename="openapi.yaml", content={})

    with pytest.raises(IntegrityError):
        async with registry_db.session() as session:
            session.add(sf_dup)
            await session.commit()
