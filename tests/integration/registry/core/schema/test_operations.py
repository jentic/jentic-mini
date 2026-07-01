"""Integration tests for the Operation ORM model."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.core.schema.operations import Operation
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


async def test_operation_round_trip(registry_db: DatabaseSession, clean_registry: None) -> None:
    """Operation stores deterministic ID, defaults deprecated to false, stores JSONB."""
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

    raw_op = {"parameters": [{"name": "petId", "in": "path"}]}
    op = Operation(
        id="op_deadbeef01",
        revision_id=rev_id,
        operation_id="getPetById",
        path="/pets/{petId}",
        method="GET",
        summary="Get a pet by ID",
        description="Returns a single pet",
        tags=["pets", "read"],
        raw_operation=raw_op,
    )

    async with registry_db.session() as session:
        session.add(op)
        await session.commit()

    async with registry_db.session() as session:
        result = await session.execute(select(Operation).where(Operation.id == "op_deadbeef01"))
        loaded = result.unique().scalar_one()

        assert loaded.revision_id == rev_id
        assert loaded.operation_id == "getPetById"
        assert loaded.path == "/pets/{petId}"
        assert loaded.method == "GET"
        assert loaded.summary == "Get a pet by ID"
        assert loaded.tags == ["pets", "read"]
        assert loaded.deprecated is False
        assert loaded.raw_operation == raw_op
        assert loaded.created_at is not None
