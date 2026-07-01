"""Integration tests for the OperationURLIndex ORM model."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.core.schema.operation_url_index import OperationURLIndex
from jentic_one.registry.core.schema.operations import Operation
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


async def test_operation_url_index_unique_constraint(
    registry_db: DatabaseSession, clean_registry: None
) -> None:
    """Duplicate (method, host, host_regex, path_template) raises IntegrityError."""
    api = Api(vendor="example.com", name="api", version="v1")

    async with registry_db.session() as session:
        session.add(api)
        await session.commit()
        api_id = api.id

    rev = ApiRevision(api_id=api_id)

    async with registry_db.session() as session:
        session.add(rev)
        await session.commit()
        rev_id = rev.id

    op = Operation(id="op_url_idx_01", revision_id=rev_id, path="/users", method="GET")

    async with registry_db.session() as session:
        session.add(op)
        await session.commit()

    idx1 = OperationURLIndex(
        operation_id="op_url_idx_01",
        revision_id=rev_id,
        method="GET",
        host="api.example.com",
        host_regex="^api\\.example\\.com$",
        path_template="/users",
        path_regex="^/users$",
        param_names=[],
        segment_count=1,
    )

    async with registry_db.session() as session:
        session.add(idx1)
        await session.commit()

    # Verify round trip
    async with registry_db.session() as session:
        result = await session.execute(
            select(OperationURLIndex).where(OperationURLIndex.operation_id == "op_url_idx_01")
        )
        loaded = result.scalar_one()
        assert loaded.method == "GET"
        assert loaded.host == "api.example.com"
        assert loaded.path_template == "/users"
        assert loaded.segment_count == 1

    # Duplicate should fail. All constrained columns are non-NULL so the unique
    # constraint fires identically on both backends (SQLite has no NULLS NOT
    # DISTINCT, so Postgres' null-coalescing semantics are not portable here).
    idx2 = OperationURLIndex(
        operation_id="op_url_idx_01",
        revision_id=rev_id,
        method="GET",
        host="api.example.com",
        host_regex="^api\\.example\\.com$",
        path_template="/users",
        path_regex="^/users$",
        param_names=[],
        segment_count=1,
    )

    with pytest.raises(IntegrityError):
        async with registry_db.session() as session:
            session.add(idx2)
            await session.commit()
