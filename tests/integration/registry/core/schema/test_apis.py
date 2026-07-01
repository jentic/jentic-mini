"""Integration tests for the Api ORM model."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


async def test_api_round_trip(registry_db: DatabaseSession, clean_registry: None) -> None:
    """An Api can be inserted and read back with all fields intact."""
    api = Api(
        vendor="github.com",
        name="rest",
        version="v3",
        display_name="GitHub REST API",
        description="GitHub's public REST API",
        icon_url="https://github.com/favicon.ico",
    )

    async with registry_db.session() as session:
        session.add(api)
        await session.commit()
        api_id = api.id

    async with registry_db.session() as session:
        result = await session.execute(select(Api).where(Api.id == api_id))
        loaded = result.scalar_one()

        assert loaded.vendor == "github.com"
        assert loaded.name == "rest"
        assert loaded.version == "v3"
        assert loaded.display_name == "GitHub REST API"
        assert loaded.description == "GitHub's public REST API"
        assert loaded.icon_url == "https://github.com/favicon.ico"
        assert loaded.revision_count == 0
        assert loaded.operation_count == 0
        assert loaded.revision == 1
        assert loaded.created_at is not None
        assert loaded.updated_at is not None
        assert loaded.current_revision_id is None


async def test_api_current_revision_pointer(
    registry_db: DatabaseSession, clean_registry: None
) -> None:
    """Setting current_revision_id loads the relationship via joined eager load."""
    api = Api(vendor="stripe.com", name="payments", version="v1")

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
        result = await session.execute(select(Api).where(Api.id == api_id))
        loaded_api = result.scalar_one()
        loaded_api.current_revision_id = rev_id
        await session.commit()

    async with registry_db.session() as session:
        result = await session.execute(select(Api).where(Api.id == api_id))
        loaded_api = result.scalar_one()
        assert loaded_api.current_revision is not None
        assert loaded_api.current_revision.id == rev_id
