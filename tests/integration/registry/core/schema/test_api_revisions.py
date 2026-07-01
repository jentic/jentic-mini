"""Integration tests for the ApiRevision ORM model."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.core.schema.operations import Operation
from jentic_one.registry.core.schema.security_schemes import SecurityScheme
from jentic_one.registry.core.schema.servers import Server
from jentic_one.registry.core.schema.spec_files import SpecFile
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


async def test_api_revision_round_trip(registry_db: DatabaseSession, clean_registry: None) -> None:
    """ApiRevision defaults state to 'draft' and links to parent Api."""
    api = Api(vendor="twilio.com", name="messaging", version="v2")

    async with registry_db.session() as session:
        session.add(api)
        await session.commit()
        api_id = api.id

    rev = ApiRevision(
        api_id=api_id,
        spec_digest="sha256:abc123",
        source_type="url",
        source_url="https://example.com/spec.yaml",
        submitted_by="bot@ci",
    )

    async with registry_db.session() as session:
        session.add(rev)
        await session.commit()
        rev_id = rev.id

    async with registry_db.session() as session:
        result = await session.execute(select(ApiRevision).where(ApiRevision.id == rev_id))
        loaded = result.scalar_one()

        assert loaded.api_id == api_id
        assert loaded.state == "draft"
        assert loaded.spec_digest == "sha256:abc123"
        assert loaded.source_type == "url"
        assert loaded.source_url == "https://example.com/spec.yaml"
        assert loaded.submitted_by == "bot@ci"
        assert loaded.operation_count == 0
        assert loaded.created_at is not None


async def test_cascade_delete_revision_removes_children(
    registry_db: DatabaseSession, clean_registry: None
) -> None:
    """Deleting an ApiRevision cascades to SpecFile, Operation, Server, SecurityScheme."""
    api = Api(vendor="acme.com", name="widgets", version="v1")

    async with registry_db.session() as session:
        session.add(api)
        await session.commit()
        api_id = api.id

    rev = ApiRevision(api_id=api_id)

    async with registry_db.session() as session:
        session.add(rev)
        await session.commit()
        rev_id = rev.id

    async with registry_db.session() as session:
        session.add(SpecFile(revision_id=rev_id, filename="openapi.json", content={"openapi": "3"}))
        session.add(Operation(id="op_abc123", revision_id=rev_id, path="/widgets", method="GET"))
        session.add(Server(revision_id=rev_id, url="https://api.acme.com"))
        session.add(
            SecurityScheme(
                revision_id=rev_id, name="bearer", type="http", raw_scheme={"type": "http"}
            )
        )
        await session.commit()

    async with registry_db.session() as session:
        result = await session.execute(select(ApiRevision).where(ApiRevision.id == rev_id))
        loaded_rev = result.scalar_one()
        await session.delete(loaded_rev)
        await session.commit()

    async with registry_db.session() as session:
        assert (
            await session.execute(select(SpecFile).where(SpecFile.revision_id == rev_id))
        ).scalar_one_or_none() is None
        assert (
            await session.execute(select(Operation).where(Operation.revision_id == rev_id))
        ).scalar_one_or_none() is None
        assert (
            await session.execute(select(Server).where(Server.revision_id == rev_id))
        ).scalar_one_or_none() is None
        assert (
            await session.execute(
                select(SecurityScheme).where(SecurityScheme.revision_id == rev_id)
            )
        ).scalar_one_or_none() is None


async def test_partial_unique_one_published_per_api(
    registry_db: DatabaseSession, clean_registry: None
) -> None:
    """Only one revision per API can be in 'published' state."""
    api = Api(vendor="example.com", name="api", version="v1")

    async with registry_db.session() as session:
        session.add(api)
        await session.commit()
        api_id = api.id

    rev1 = ApiRevision(api_id=api_id, state="published")

    async with registry_db.session() as session:
        session.add(rev1)
        await session.commit()

    rev2 = ApiRevision(api_id=api_id, state="published")

    with pytest.raises(IntegrityError):
        async with registry_db.session() as session:
            session.add(rev2)
            await session.commit()
