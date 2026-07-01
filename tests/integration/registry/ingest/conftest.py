"""Fixtures for ingest pipeline integration tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete, update

from jentic_one.registry.core.schema.api_revisions import ApiRevision
from jentic_one.registry.core.schema.apis import Api
from jentic_one.registry.core.schema.operation_url_index import OperationURLIndex
from jentic_one.registry.core.schema.operations import Operation
from jentic_one.registry.core.schema.security_schemes import SecurityScheme, SecuritySchemeFlow
from jentic_one.registry.core.schema.servers import Server, ServerVariable
from jentic_one.registry.core.schema.spec_files import SpecFile
from jentic_one.shared.context import Context
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_registry(registry_db: DatabaseSession) -> AsyncGenerator[None, None]:
    """Truncate all registry tables before and after each test."""

    async def _truncate() -> None:
        async with registry_db.session() as session:
            await session.execute(delete(OperationURLIndex))
            await session.execute(delete(SecuritySchemeFlow))
            await session.execute(delete(SecurityScheme))
            await session.execute(delete(ServerVariable))
            await session.execute(delete(Server))
            await session.execute(delete(Operation))
            await session.execute(delete(SpecFile))
            await session.execute(update(Api).values(current_revision_id=None))
            await session.execute(delete(ApiRevision))
            await session.execute(delete(Api))
            await session.commit()

    await _truncate()
    yield
    await _truncate()


@pytest.fixture()
def ingest_context(integration_context: Context) -> Context:
    """Provide the connected integration Context for ingest tests."""
    return integration_context
