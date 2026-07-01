"""Integration tests for UserPermissionGrantRepository against real PostgreSQL."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete

from jentic_one.admin.core.schema.user_permission_grants import UserPermissionGrant
from jentic_one.admin.core.schema.users import User
from jentic_one.admin.repos import UserPermissionGrantRepository, UserRepository
from jentic_one.shared.db.session import DatabaseSession

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_permissions(admin_db: DatabaseSession) -> AsyncGenerator[None, None]:
    async with admin_db.session() as session:
        await session.execute(delete(UserPermissionGrant))
        await session.execute(delete(User))
        await session.commit()
    yield
    async with admin_db.session() as session:
        await session.execute(delete(UserPermissionGrant))
        await session.execute(delete(User))
        await session.commit()


@pytest.fixture()
async def test_user(admin_db: DatabaseSession, clean_permissions: None) -> str:
    async with admin_db.session() as session:
        user = await UserRepository.create(
            session,
            email="perm-test@example.com",
            first_name="Perm",
            last_name="Test",
            created_by="usr_test",
        )
        await session.commit()
        return user.id


async def test_set_permissions_and_get(admin_db: DatabaseSession, test_user: str) -> None:
    async with admin_db.session() as session:
        grants = await UserPermissionGrantRepository.set_permissions(
            session,
            test_user,
            permissions={"users:read", "users:manage", "toolkits:read"},
            granted_by="usr_admin000000000000000000",
            created_by="usr_test",
        )
        await session.commit()
        assert len(grants) == 3
        assert all(g.id.startswith("perm_") for g in grants)

    async with admin_db.session() as session:
        loaded = await UserPermissionGrantRepository.get_grants_for_user(session, test_user)
        perms = {g.permission for g in loaded}
        assert perms == {"users:read", "users:manage", "toolkits:read"}
        assert all(g.granted_by == "usr_admin000000000000000000" for g in loaded)


async def test_set_permissions_replaces(admin_db: DatabaseSession, test_user: str) -> None:
    async with admin_db.session() as session:
        await UserPermissionGrantRepository.set_permissions(
            session, test_user, permissions={"users:read", "users:manage"}, created_by="usr_test"
        )
        await session.commit()

    async with admin_db.session() as session:
        await UserPermissionGrantRepository.set_permissions(
            session, test_user, permissions={"toolkits:read"}, created_by="usr_test"
        )
        await session.commit()

    async with admin_db.session() as session:
        grants = await UserPermissionGrantRepository.get_grants_for_user(session, test_user)
        perms = {g.permission for g in grants}
        assert perms == {"toolkits:read"}


async def test_get_users_with_permission(admin_db: DatabaseSession, test_user: str) -> None:
    async with admin_db.session() as session:
        user2 = await UserRepository.create(
            session,
            email="perm-test2@example.com",
            first_name="Perm2",
            last_name="Test2",
            created_by="usr_test",
        )
        await session.commit()
        user2_id = user2.id

    async with admin_db.session() as session:
        await UserPermissionGrantRepository.set_permissions(
            session, test_user, permissions={"org:admin", "users:read"}, created_by="usr_test"
        )
        await UserPermissionGrantRepository.set_permissions(
            session, user2_id, permissions={"users:read"}, created_by="usr_test"
        )
        await session.commit()

    async with admin_db.session() as session:
        admin_grants = await UserPermissionGrantRepository.get_users_with_permission(
            session, "org:admin"
        )
        assert len(admin_grants) == 1
        assert admin_grants[0].user_id == test_user

        read_grants = await UserPermissionGrantRepository.get_users_with_permission(
            session, "users:read"
        )
        assert len(read_grants) == 2


async def test_empty_permissions_clears_all(admin_db: DatabaseSession, test_user: str) -> None:
    async with admin_db.session() as session:
        await UserPermissionGrantRepository.set_permissions(
            session, test_user, permissions={"users:read"}, created_by="usr_test"
        )
        await session.commit()

    async with admin_db.session() as session:
        await UserPermissionGrantRepository.set_permissions(
            session, test_user, permissions=set(), created_by="usr_test"
        )
        await session.commit()

    async with admin_db.session() as session:
        grants = await UserPermissionGrantRepository.get_grants_for_user(session, test_user)
        assert len(grants) == 0
