"""Integration tests for transaction recovery against a real database."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text

from jentic_one.shared.db.errors import DatabaseIntegrityError
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


@pytest.fixture()
async def _clean_txn_test_users(admin_db: DatabaseSession) -> AsyncGenerator[None, None]:
    """Remove test rows before and after each test."""
    async with admin_db.session() as session:
        await session.execute(text("DELETE FROM users WHERE email LIKE '%@txn-recovery.local'"))
        await session.commit()
    yield
    async with admin_db.session() as session:
        await session.execute(text("DELETE FROM users WHERE email LIKE '%@txn-recovery.local'"))
        await session.commit()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_clean_txn_test_users")
async def test_integrity_error_rolls_back_cleanly(admin_db: DatabaseSession) -> None:
    """Duplicate unique key triggers DatabaseIntegrityError with clean rollback."""
    async with admin_db.transaction() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, email, first_name, last_name) "
                "VALUES ('txn-rec-1', 'alice@txn-recovery.local', 'Alice', 'Smith')"
            )
        )

    with pytest.raises(DatabaseIntegrityError):
        async with admin_db.transaction() as session:
            await session.execute(
                text(
                    "INSERT INTO users (id, email, first_name, last_name) "
                    "VALUES ('txn-rec-2', 'alice@txn-recovery.local', 'Bob', 'Jones')"
                )
            )

    async with admin_db.session() as session:
        result = await session.execute(
            text("SELECT count(*) FROM users WHERE email = 'alice@txn-recovery.local'")
        )
        assert result.scalar() == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("_clean_txn_test_users")
async def test_session_recovers_after_integrity_failure(admin_db: DatabaseSession) -> None:
    """A subsequent transaction succeeds after a prior integrity failure."""
    async with admin_db.transaction() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, email, first_name, last_name) "
                "VALUES ('txn-rec-3', 'carol@txn-recovery.local', 'Carol', 'White')"
            )
        )

    with pytest.raises(DatabaseIntegrityError):
        async with admin_db.transaction() as session:
            await session.execute(
                text(
                    "INSERT INTO users (id, email, first_name, last_name) "
                    "VALUES ('txn-rec-4', 'carol@txn-recovery.local', 'Dave', 'Black')"
                )
            )

    async with admin_db.transaction() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, email, first_name, last_name) "
                "VALUES ('txn-rec-5', 'eve@txn-recovery.local', 'Eve', 'Green')"
            )
        )

    async with admin_db.session() as session:
        result = await session.execute(
            text(
                "SELECT count(*) FROM users "
                "WHERE email IN ('carol@txn-recovery.local', 'eve@txn-recovery.local')"
            )
        )
        assert result.scalar() == 2


@pytest.mark.asyncio
@pytest.mark.usefixtures("_clean_txn_test_users")
async def test_normal_commit_persists_rows(admin_db: DatabaseSession) -> None:
    """Normal transaction commits persist rows to the database."""
    async with admin_db.transaction() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, email, first_name, last_name) "
                "VALUES ('txn-rec-6', 'frank@txn-recovery.local', 'Frank', 'Red')"
            )
        )

    async with admin_db.session() as session:
        result = await session.execute(text("SELECT first_name FROM users WHERE id = 'txn-rec-6'"))
        assert result.scalar() == "Frank"
