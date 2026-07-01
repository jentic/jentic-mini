"""Integration test proving advisory lock serializes concurrent catalog refreshes."""

from __future__ import annotations

import asyncio
import os

import pytest

from jentic_one.registry.repos.catalog_repo import CatalogRepository
from jentic_one.shared.db.session import DatabaseSession

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("JENTIC_TEST_BACKEND", "postgres").lower() == "sqlite",
        reason="advisory locks require Postgres",
    ),
]


async def test_advisory_lock_serializes_concurrent_callers(
    registry_db: DatabaseSession,
) -> None:
    """Two concurrent transactions: exactly one acquires the lock, the other does not."""
    results: list[bool] = []
    barrier = asyncio.Barrier(2)

    async def attempt() -> bool:
        async with registry_db.transaction() as session:
            acquired = await CatalogRepository.try_acquire_refresh_lock(session)
            results.append(acquired)
            await barrier.wait()
        return acquired

    outcomes = await asyncio.gather(attempt(), attempt())
    assert sorted(outcomes) == [False, True]
