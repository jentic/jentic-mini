"""Tests for DatabaseSession.transaction() context manager."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from jentic_one.shared.db.errors import DatabaseIntegrityError
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_transaction_commits_on_clean_exit(admin_db: DatabaseSession) -> None:
    """Session is committed when the block exits cleanly."""
    async with admin_db.transaction() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_transaction_rolls_back_on_exception(admin_db: DatabaseSession) -> None:
    """Arbitrary exception triggers rollback; original exception re-raised."""

    class CustomError(Exception):
        pass

    with pytest.raises(CustomError):
        async with admin_db.transaction() as session:
            await session.execute(text("SELECT 1"))
            raise CustomError("boom")


@pytest.mark.asyncio
async def test_transaction_integrity_error_wraps(admin_db: DatabaseSession) -> None:
    """IntegrityError is wrapped in DatabaseIntegrityError."""
    async with admin_db.session() as session:
        await session.execute(text("DELETE FROM users WHERE email = 'dup-txn-test@test.local'"))
        await session.commit()

    async with admin_db.transaction() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, email, first_name, last_name) "
                "VALUES ('txn-integ-1', 'dup-txn-test@test.local', 'A', 'B')"
            )
        )

    with pytest.raises(DatabaseIntegrityError):
        async with admin_db.transaction() as session:
            await session.execute(
                text(
                    "INSERT INTO users (id, email, first_name, last_name) "
                    "VALUES ('txn-integ-2', 'dup-txn-test@test.local', 'C', 'D')"
                )
            )

    async with admin_db.session() as session:
        await session.execute(text("DELETE FROM users WHERE id IN ('txn-integ-1', 'txn-integ-2')"))
        await session.commit()


@pytest.mark.asyncio
async def test_transaction_session_usable_after_integrity_error(
    admin_db: DatabaseSession,
) -> None:
    """DatabaseSession is still usable after a prior integrity failure."""
    async with admin_db.session() as session:
        await session.execute(text("DELETE FROM users WHERE email = 'recover-txn@test.local'"))
        await session.commit()

    async with admin_db.transaction() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, email, first_name, last_name) "
                "VALUES ('txn-recov-1', 'recover-txn@test.local', 'A', 'B')"
            )
        )

    with pytest.raises(DatabaseIntegrityError):
        async with admin_db.transaction() as session:
            await session.execute(
                text(
                    "INSERT INTO users (id, email, first_name, last_name) "
                    "VALUES ('txn-recov-2', 'recover-txn@test.local', 'C', 'D')"
                )
            )

    async with admin_db.transaction() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    async with admin_db.session() as session:
        await session.execute(text("DELETE FROM users WHERE id IN ('txn-recov-1', 'txn-recov-2')"))
        await session.commit()


@pytest.mark.asyncio
async def test_transaction_rollback_does_not_persist(admin_db: DatabaseSession) -> None:
    """Data written inside a failed transaction is not persisted."""
    test_id = "txn-rollback-check"

    async with admin_db.session() as session:
        await session.execute(text(f"DELETE FROM users WHERE id = '{test_id}'"))
        await session.commit()

    class CustomError(Exception):
        pass

    with pytest.raises(CustomError):
        async with admin_db.transaction() as session:
            await session.execute(
                text(
                    f"INSERT INTO users (id, email, first_name, last_name) "
                    f"VALUES ('{test_id}', 'rollback@test.local', 'A', 'B')"
                )
            )
            raise CustomError("abort")

    async with admin_db.session() as session:
        result = await session.execute(text(f"SELECT count(*) FROM users WHERE id = '{test_id}'"))
        assert result.scalar() == 0
