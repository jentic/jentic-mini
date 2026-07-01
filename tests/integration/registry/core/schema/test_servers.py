"""Integration tests for the Server and ServerVariable ORM models."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.core.schema.servers import Server, ServerVariable
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


async def test_server_and_variable_round_trip(
    registry_db: DatabaseSession, clean_registry: None
) -> None:
    """Server with variables loads eagerly via joined strategy."""
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

    server = Server(
        revision_id=rev_id,
        url="https://{env}.example.com/v1",
        description="Main API server",
    )

    async with registry_db.session() as session:
        session.add(server)
        await session.commit()
        server_id = server.id

    var = ServerVariable(
        server_id=server_id,
        name="env",
        default_value="production",
        description="Environment selector",
        enum=["production", "staging", "sandbox"],
    )

    async with registry_db.session() as session:
        session.add(var)
        await session.commit()

    async with registry_db.session() as session:
        result = await session.execute(select(Server).where(Server.id == server_id))
        loaded = result.unique().scalar_one()

        assert loaded.url == "https://{env}.example.com/v1"
        assert loaded.description == "Main API server"
        assert len(loaded.variables) == 1
        assert loaded.variables[0].name == "env"
        assert loaded.variables[0].default_value == "production"
        assert loaded.variables[0].enum == ["production", "staging", "sandbox"]
