"""Integration tests for InviteTokenRepository against real PostgreSQL."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from jentic_one.admin.core.schema.invite_tokens import InviteToken
from jentic_one.admin.core.schema.users import User
from jentic_one.admin.repos import InviteTokenRepository, UserRepository
from jentic_one.admin.services.errors import InviteTokenNotFoundError
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_invite_tokens(admin_db: DatabaseSession) -> AsyncGenerator[None, None]:
    async with admin_db.session() as session:
        await session.execute(delete(InviteToken))
        await session.execute(delete(User))
        await session.commit()
    yield
    async with admin_db.session() as session:
        await session.execute(delete(InviteToken))
        await session.execute(delete(User))
        await session.commit()


@pytest.fixture()
async def test_user(admin_db: DatabaseSession, clean_invite_tokens: None) -> str:
    async with admin_db.session() as session:
        user = await UserRepository.create(
            session,
            email="invite-test@example.com",
            first_name="Invite",
            last_name="Test",
            created_by="usr_test",
        )
        await session.commit()
        return user.id


async def test_create_generates_ksuid(admin_db: DatabaseSession, test_user: str) -> None:
    async with admin_db.session() as session:
        token = await InviteTokenRepository.create(
            session,
            user_id=test_user,
            token_hash="hash_abc123",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            created_by="usr_test",
        )
        await session.commit()
        assert token.id.startswith("inv_")
        assert len(token.id) == 28


async def test_get_by_token_hash(admin_db: DatabaseSession, test_user: str) -> None:
    async with admin_db.session() as session:
        await InviteTokenRepository.create(
            session,
            user_id=test_user,
            token_hash="unique_hash_xyz",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            created_by="usr_test",
        )
        await session.commit()

    async with admin_db.session() as session:
        found = await InviteTokenRepository.get_by_token_hash(session, "unique_hash_xyz")
        assert found is not None
        assert found.user_id == test_user

        not_found = await InviteTokenRepository.get_by_token_hash(session, "nonexistent")
        assert not_found is None


async def test_redeem(admin_db: DatabaseSession, test_user: str) -> None:
    async with admin_db.session() as session:
        token = await InviteTokenRepository.create(
            session,
            user_id=test_user,
            token_hash="redeem_hash_001",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            created_by="usr_test",
        )
        await session.commit()
        token_id = token.id

    async with admin_db.session() as session:
        redeemed = await InviteTokenRepository.redeem(session, token_id)
        await session.commit()
        assert redeemed.redeemed_at is not None


async def test_redeem_not_found(admin_db: DatabaseSession, clean_invite_tokens: None) -> None:
    async with admin_db.session() as session:
        with pytest.raises(InviteTokenNotFoundError):
            await InviteTokenRepository.redeem(session, "inv_nonexistent0000000000")


async def test_get_active_for_user(admin_db: DatabaseSession, test_user: str) -> None:
    async with admin_db.session() as session:
        await InviteTokenRepository.create(
            session,
            user_id=test_user,
            token_hash="active_hash_1",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            created_by="usr_test",
        )
        expired = await InviteTokenRepository.create(
            session,
            user_id=test_user,
            token_hash="expired_hash_1",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            created_by="usr_test",
        )
        await session.commit()
        expired_id = expired.id

    async with admin_db.session() as session:
        redeemed_token = await InviteTokenRepository.create(
            session,
            user_id=test_user,
            token_hash="redeemed_hash_1",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            created_by="usr_test",
        )
        await session.commit()
        redeemed_id = redeemed_token.id

    async with admin_db.session() as session:
        await InviteTokenRepository.redeem(session, redeemed_id)
        await session.commit()

    async with admin_db.session() as session:
        active = await InviteTokenRepository.get_active_for_user(session, test_user)
        assert len(active) == 1
        assert active[0].token_hash == "active_hash_1"
        assert all(t.id != expired_id for t in active)
        assert all(t.id != redeemed_id for t in active)
