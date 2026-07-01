"""Integration tests for InviteService against real PostgreSQL."""

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
    InvalidInputError,
    InviteTokenAlreadyRedeemedError,
    InviteTokenNotFoundError,
)
from jentic_one.admin.services.invite_service import InviteService
from jentic_one.admin.services.schemas.users import UserCreatePayload
from jentic_one.admin.services.user_service import UserService
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.context import Context
from jentic_one.shared.models import InviteState

pytestmark = pytest.mark.integration


@pytest.fixture()
async def admin_user(integration_context: Context) -> AsyncGenerator[str, None]:
    """Create an admin user for creating other users."""
    ctx = integration_context
    async with ctx.admin_db.session() as session:
        user = await UserRepository.create(
            session,
            email="invsvc-admin@test.local",
            first_name="Admin",
            last_name="Inv",
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


async def test_issue_and_redeem(integration_context: Context, admin_user: str) -> None:
    ctx = integration_context
    user_svc = UserService(ctx)
    invite_svc = InviteService(ctx)

    created = await user_svc.create(
        UserCreatePayload(email="invite-test@test.local", first_name="Inv", last_name="Test"),
        identity=Identity(sub=admin_user, email="test@local"),
    )
    user_id = created.user.id
    token = created.invite_token

    assert token.startswith("inv_")

    result = await invite_svc.redeem(token, "my-secure-password")
    assert result.access_token
    assert result.token_type == "bearer"

    # Cleanup
    async with ctx.admin_db.session() as session:
        await session.execute(delete(InviteToken).where(InviteToken.user_id == user_id))
        await session.execute(
            delete(UserPermissionGrant).where(UserPermissionGrant.user_id == user_id)
        )
        await session.execute(delete(UserSecret).where(UserSecret.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def test_reissue_invalidates_old_token(integration_context: Context, admin_user: str) -> None:
    ctx = integration_context
    user_svc = UserService(ctx)
    invite_svc = InviteService(ctx)

    created = await user_svc.create(
        UserCreatePayload(email="reissue-inv@test.local", first_name="Re", last_name="Issue"),
        identity=Identity(sub=admin_user, email="test@local"),
    )
    user_id = created.user.id
    old_token = created.invite_token

    new_invite = await invite_svc.reissue(
        user_id, identity=Identity(sub="usr_test", email="test@local")
    )
    assert new_invite.token.startswith("inv_")
    assert new_invite.token != old_token

    # Old token should be invalid (already redeemed)
    with pytest.raises(InviteTokenAlreadyRedeemedError):
        await invite_svc.redeem(old_token, "some-password")

    # Cleanup
    async with ctx.admin_db.session() as session:
        await session.execute(delete(InviteToken).where(InviteToken.user_id == user_id))
        await session.execute(
            delete(UserPermissionGrant).where(UserPermissionGrant.user_id == user_id)
        )
        await session.execute(delete(UserSecret).where(UserSecret.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def test_redeem_already_redeemed_raises(
    integration_context: Context, admin_user: str
) -> None:
    ctx = integration_context
    user_svc = UserService(ctx)
    invite_svc = InviteService(ctx)

    created = await user_svc.create(
        UserCreatePayload(email="double-redeem@test.local", first_name="Double", last_name="R"),
        identity=Identity(sub=admin_user, email="test@local"),
    )
    user_id = created.user.id
    token = created.invite_token

    await invite_svc.redeem(token, "first-password")

    with pytest.raises(InviteTokenAlreadyRedeemedError):
        await invite_svc.redeem(token, "second-password")

    # Cleanup
    async with ctx.admin_db.session() as session:
        await session.execute(delete(InviteToken).where(InviteToken.user_id == user_id))
        await session.execute(
            delete(UserPermissionGrant).where(UserPermissionGrant.user_id == user_id)
        )
        await session.execute(delete(UserSecret).where(UserSecret.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def test_redeem_not_found(integration_context: Context) -> None:
    invite_svc = InviteService(integration_context)
    with pytest.raises(InviteTokenNotFoundError):
        await invite_svc.redeem("inv_nonexistent_token_value", "long-enough-pw")


async def test_redeem_short_password_raises(integration_context: Context) -> None:
    invite_svc = InviteService(integration_context)
    with pytest.raises(InvalidInputError, match="at least 12 characters"):
        await invite_svc.redeem("inv_doesnt_matter", "short")
