"""Integration tests for UserService against real PostgreSQL."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete

from jentic_one.admin.core.schema.invite_tokens import InviteToken
from jentic_one.admin.core.schema.user_permission_grants import UserPermissionGrant
from jentic_one.admin.core.schema.user_secrets import UserSecret
from jentic_one.admin.core.schema.users import User
from jentic_one.admin.repos import (
    UserPermissionGrantRepository,
    UserRepository,
    UserSecretRepository,
)
from jentic_one.admin.services._support.passwords import hash_password
from jentic_one.admin.services.errors import (
    ConflictError,
    EmailAlreadyExistsError,
    UserNotFoundError,
)
from jentic_one.admin.services.schemas.users import UserCreatePayload, UserUpdatePayload
from jentic_one.admin.services.user_service import UserService
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.context import Context
from jentic_one.shared.models import InviteState

pytestmark = pytest.mark.integration


@pytest.fixture()
async def admin_user(integration_context: Context) -> AsyncGenerator[str, None]:
    """Create an admin user for granting permissions."""
    ctx = integration_context
    async with ctx.admin_db.session() as session:
        user = await UserRepository.create(
            session,
            email="usrsvc-admin@test.local",
            first_name="Admin",
            last_name="User",
            invite_state=InviteState.REDEEMED,
            created_by="usr_test",
        )
        await UserSecretRepository.create(
            session,
            user_id=user.id,
            password_hash=hash_password("admin-pass"),
            created_by="usr_test",
        )
        await UserPermissionGrantRepository.set_permissions(
            session, user.id, permissions={"org:admin"}, granted_by=None, created_by="usr_test"
        )
        await session.commit()
    yield user.id

    # Cleanup
    async with ctx.admin_db.session() as session:
        await session.execute(delete(InviteToken).where(InviteToken.user_id == user.id))
        await session.execute(
            delete(UserPermissionGrant).where(UserPermissionGrant.user_id == user.id)
        )
        await session.execute(delete(UserSecret).where(UserSecret.user_id == user.id))
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()


async def test_create_user(integration_context: Context, admin_user: str) -> None:
    ctx = integration_context
    service = UserService(ctx)
    created = await service.create(
        UserCreatePayload(
            email="new-user@test.local",
            first_name="New",
            last_name="User",
            permissions=["users:read"],
        ),
        identity=Identity(sub=admin_user, email="test@local"),
    )

    assert created.user.email == "new-user@test.local"
    assert created.user.invite_state == "pending"
    assert created.invite_token.startswith("inv_")
    assert "users:read" in created.user.assigned

    # Cleanup
    user_id = created.user.id
    async with ctx.admin_db.session() as session:
        await session.execute(delete(InviteToken).where(InviteToken.user_id == user_id))
        await session.execute(
            delete(UserPermissionGrant).where(UserPermissionGrant.user_id == user_id)
        )
        await session.execute(delete(UserSecret).where(UserSecret.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def test_create_duplicate_email_raises(integration_context: Context, admin_user: str) -> None:
    ctx = integration_context
    service = UserService(ctx)

    created = await service.create(
        UserCreatePayload(email="dup@test.local", first_name="First", last_name="User"),
        identity=Identity(sub=admin_user, email="test@local"),
    )
    user_id = created.user.id

    with pytest.raises(EmailAlreadyExistsError):
        await service.create(
            UserCreatePayload(email="dup@test.local", first_name="Second", last_name="User"),
            identity=Identity(sub=admin_user, email="test@local"),
        )

    # Cleanup
    async with ctx.admin_db.session() as session:
        await session.execute(delete(InviteToken).where(InviteToken.user_id == user_id))
        await session.execute(
            delete(UserPermissionGrant).where(UserPermissionGrant.user_id == user_id)
        )
        await session.execute(delete(UserSecret).where(UserSecret.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def test_get_by_id(integration_context: Context, admin_user: str) -> None:
    ctx = integration_context
    service = UserService(ctx)

    created = await service.create(
        UserCreatePayload(email="getme@test.local", first_name="Get", last_name="Me"),
        identity=Identity(sub=admin_user, email="test@local"),
    )
    user_id = created.user.id

    view = await service.get_by_id(user_id)
    assert view.id == user_id
    assert view.email == "getme@test.local"

    # Cleanup
    async with ctx.admin_db.session() as session:
        await session.execute(delete(InviteToken).where(InviteToken.user_id == user_id))
        await session.execute(
            delete(UserPermissionGrant).where(UserPermissionGrant.user_id == user_id)
        )
        await session.execute(delete(UserSecret).where(UserSecret.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def test_get_by_id_not_found(integration_context: Context) -> None:
    service = UserService(integration_context)
    with pytest.raises(UserNotFoundError):
        await service.get_by_id("usr_nonexistent000000000000")


async def test_list(integration_context: Context, admin_user: str) -> None:
    ctx = integration_context
    service = UserService(ctx)

    created_ids = []
    for i in range(3):
        created = await service.create(
            UserCreatePayload(
                email=f"list-user-{i}@test.local", first_name=f"User{i}", last_name="List"
            ),
            identity=Identity(sub=admin_user, email="test@local"),
        )
        created_ids.append(created.user.id)

    page = await service.list_all(limit=50)
    page_ids = [u.id for u in page.data]
    for uid in created_ids:
        assert uid in page_ids

    # Cleanup
    async with ctx.admin_db.session() as session:
        for uid in created_ids:
            await session.execute(delete(InviteToken).where(InviteToken.user_id == uid))
            await session.execute(
                delete(UserPermissionGrant).where(UserPermissionGrant.user_id == uid)
            )
            await session.execute(delete(UserSecret).where(UserSecret.user_id == uid))
            await session.execute(delete(User).where(User.id == uid))
        await session.commit()


async def test_update(integration_context: Context, admin_user: str) -> None:
    ctx = integration_context
    service = UserService(ctx)

    created = await service.create(
        UserCreatePayload(email="update-me@test.local", first_name="Old", last_name="Name"),
        identity=Identity(sub=admin_user, email="test@local"),
    )
    user_id = created.user.id

    updated = await service.update(
        user_id,
        UserUpdatePayload(first_name="New"),
        identity=Identity(sub="usr_test", email="test@local"),
    )
    assert updated.first_name == "New"
    assert updated.last_name == "Name"

    # Cleanup
    async with ctx.admin_db.session() as session:
        await session.execute(delete(InviteToken).where(InviteToken.user_id == user_id))
        await session.execute(
            delete(UserPermissionGrant).where(UserPermissionGrant.user_id == user_id)
        )
        await session.execute(delete(UserSecret).where(UserSecret.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def test_delete_anonymises(integration_context: Context, admin_user: str) -> None:
    ctx = integration_context
    service = UserService(ctx)

    created = await service.create(
        UserCreatePayload(email="delete-me@test.local", first_name="Del", last_name="User"),
        identity=Identity(sub=admin_user, email="test@local"),
    )
    user_id = created.user.id

    await service.delete(user_id, identity=Identity(sub="usr_test", email="test@local"))

    async with ctx.admin_db.session() as session:
        user = await UserRepository.get_by_id(session, user_id)
    assert user is not None
    assert user.active is False
    assert user.email.startswith("deleted-") and user.email.endswith("@local")

    # Cleanup
    async with ctx.admin_db.session() as session:
        await session.execute(delete(InviteToken).where(InviteToken.user_id == user_id))
        await session.execute(
            delete(UserPermissionGrant).where(UserPermissionGrant.user_id == user_id)
        )
        await session.execute(delete(UserSecret).where(UserSecret.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def test_delete_not_found(integration_context: Context) -> None:
    service = UserService(integration_context)
    with pytest.raises(UserNotFoundError):
        await service.delete(
            "usr_nonexistent000000000000",
            identity=Identity(sub="usr_test", email="test@local"),
        )


async def test_disable_and_enable(integration_context: Context, admin_user: str) -> None:
    ctx = integration_context
    service = UserService(ctx)

    created = await service.create(
        UserCreatePayload(email="toggle@test.local", first_name="Toggle", last_name="User"),
        identity=Identity(sub=admin_user, email="test@local"),
    )
    user_id = created.user.id

    await service.disable(user_id, identity=Identity(sub="usr_test", email="test@local"))
    user_after_disable = await service.get_by_id(user_id)
    assert user_after_disable.active is False

    await service.enable(user_id, identity=Identity(sub="usr_test", email="test@local"))
    user_after_enable = await service.get_by_id(user_id)
    assert user_after_enable.active is True

    # Cleanup
    async with ctx.admin_db.session() as session:
        await session.execute(delete(InviteToken).where(InviteToken.user_id == user_id))
        await session.execute(
            delete(UserPermissionGrant).where(UserPermissionGrant.user_id == user_id)
        )
        await session.execute(delete(UserSecret).where(UserSecret.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def test_reissue_invite(integration_context: Context, admin_user: str) -> None:
    ctx = integration_context
    service = UserService(ctx)

    created = await service.create(
        UserCreatePayload(email="reissue@test.local", first_name="Reissue", last_name="User"),
        identity=Identity(sub=admin_user, email="test@local"),
    )
    user_id = created.user.id

    invite = await service.reissue_invite(
        user_id, identity=Identity(sub="usr_test", email="test@local")
    )
    assert invite.token.startswith("inv_")
    assert invite.token != created.invite_token

    # Cleanup
    async with ctx.admin_db.session() as session:
        await session.execute(delete(InviteToken).where(InviteToken.user_id == user_id))
        await session.execute(
            delete(UserPermissionGrant).where(UserPermissionGrant.user_id == user_id)
        )
        await session.execute(delete(UserSecret).where(UserSecret.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def test_reissue_invite_redeemed_raises(
    integration_context: Context, admin_user: str
) -> None:
    ctx = integration_context
    async with ctx.admin_db.session() as session:
        user = await UserRepository.create(
            session,
            email="redeemed-inv@test.local",
            first_name="Redeemed",
            last_name="User",
            invite_state=InviteState.REDEEMED,
            created_by="usr_test",
        )
        await UserSecretRepository.create(session, user_id=user.id, created_by="usr_test")
        await session.commit()
    user_id = user.id

    service = UserService(ctx)
    with pytest.raises(ConflictError):
        await service.reissue_invite(user_id, identity=Identity(sub="usr_test", email="test@local"))

    # Cleanup
    async with ctx.admin_db.session() as session:
        await session.execute(delete(UserSecret).where(UserSecret.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()
