"""Integration tests for ServerRepository."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.core.schema.servers import Server, ServerVariable
from jentic_one.registry.repos.operation_repo import OperationInput, OperationRepository
from jentic_one.registry.repos.server_repo import ServerRepository
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


async def test_store_servers_basic(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """store_servers creates server entries and returns their UUIDs."""
    _, rev = sample_revision
    servers_data = [
        {"url": "https://api.example.com", "description": "Production"},
        {"url": "https://staging.example.com"},
    ]

    async with registry_db.session() as session:
        ids = await ServerRepository.store_servers(
            session, revision_id=rev.id, servers_data=servers_data, created_by="usr_test"
        )
        await session.commit()

    assert len(ids) == 2


async def test_store_servers_with_variables(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """store_servers creates server variables linked to servers."""
    _, rev = sample_revision
    servers_data = [
        {
            "url": "https://{env}.example.com",
            "variables": {
                "env": {
                    "default": "production",
                    "description": "Server environment",
                    "enum": ["production", "staging"],
                }
            },
        }
    ]

    async with registry_db.session() as session:
        ids = await ServerRepository.store_servers(
            session, revision_id=rev.id, servers_data=servers_data, created_by="usr_test"
        )
        await session.commit()
        server_id = ids[0]

    async with registry_db.session() as session:
        server = await session.get(Server, server_id)
        assert server is not None
        assert len(server.variables) == 1
        var = server.variables[0]
        assert var.name == "env"
        assert var.default_value == "production"
        assert var.description == "Server environment"
        assert var.enum == ["production", "staging"]


async def test_store_servers_with_operation_id(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """store_servers can associate servers with a specific operation."""
    _, rev = sample_revision
    ops = [OperationInput(path="/specific", method="GET")]

    async with registry_db.session() as session:
        op_ids = await OperationRepository.bulk_create(session, rev.id, ops, created_by="usr_test")
        await session.commit()

    servers_data = [{"url": "https://op-specific.example.com"}]

    async with registry_db.session() as session:
        ids = await ServerRepository.store_servers(
            session,
            revision_id=rev.id,
            servers_data=servers_data,
            operation_id=op_ids[0],
            created_by="usr_test",
        )
        await session.commit()
        server_id = ids[0]

    async with registry_db.session() as session:
        server = await session.get(Server, server_id)
        assert server is not None
        assert server.operation_id == op_ids[0]


async def test_delete_for_revision_cascades_to_variables(
    registry_db: DatabaseSession, sample_revision: tuple[Api, ApiRevision]
) -> None:
    """delete_for_revision removes servers and cascades to variables."""
    _, rev = sample_revision
    servers_data = [
        {
            "url": "https://example.com",
            "variables": {"port": {"default": "8080"}},
        }
    ]

    async with registry_db.session() as session:
        await ServerRepository.store_servers(
            session, revision_id=rev.id, servers_data=servers_data, created_by="usr_test"
        )
        await session.commit()

    async with registry_db.session() as session:
        await ServerRepository.delete_for_revision(session, rev.id)
        await session.commit()

    async with registry_db.session() as session:
        result = await session.execute(select(Server).where(Server.revision_id == rev.id))
        assert result.scalars().all() == []
        result = await session.execute(select(ServerVariable))
        assert result.scalars().all() == []
