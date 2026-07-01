"""Integration tests verifying real database connectivity through Context."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from jentic_one.shared.context import Context

pytestmark = pytest.mark.integration


async def test_connect_all_databases(integration_context: Context) -> None:
    """Context connects to all three databases and can execute queries."""
    for db in (
        integration_context.registry_db,
        integration_context.admin_db,
        integration_context.control_db,
    ):
        async with db.session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
