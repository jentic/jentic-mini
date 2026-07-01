"""Integration tests for HealthService against real PostgreSQL.

Setup detection is now purely "are there any users?" (the no-credential
first-run model): an empty users table means setup is required, any user means
it's done. The former seeded ``admin@local`` / ``change_admin_password`` model
is gone.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete

from jentic_one.admin.core.schema.invite_tokens import InviteToken
from jentic_one.admin.core.schema.setup_sentinel import SetupSentinel
from jentic_one.admin.core.schema.user_permission_grants import UserPermissionGrant
from jentic_one.admin.core.schema.user_secrets import UserSecret
from jentic_one.admin.core.schema.users import User
from jentic_one.admin.repos import UserRepository, UserSecretRepository
from jentic_one.admin.services._support.passwords import hash_password
from jentic_one.admin.services.health_service import HealthService
from jentic_one.shared.context import Context
from jentic_one.shared.models import InviteState

pytestmark = pytest.mark.integration


@pytest.fixture()
async def _empty_users(integration_context: Context) -> AsyncGenerator[None, None]:
    """Guarantee an empty users table around the test (first-run state).

    The shared integration DB may carry users (or a leftover setup sentinel) from
    other tests, so we clear all user rows (and dependents) plus the singleton
    sentinel before AND after the test — symmetric with the other ``_empty_users``
    fixtures — so neither the user created by ``test_healthy_once_a_user_exists``
    nor a stale sentinel leaks into other tests sharing the integration DB.
    """

    async def _wipe() -> None:
        async with integration_context.admin_db.session() as session:
            await session.execute(delete(InviteToken))
            await session.execute(delete(UserPermissionGrant))
            await session.execute(delete(UserSecret))
            await session.execute(delete(User))
            await session.execute(delete(SetupSentinel))
            await session.commit()

    await _wipe()
    yield
    await _wipe()


async def test_setup_required_when_no_users(
    integration_context: Context, _empty_users: None
) -> None:
    service = HealthService(integration_context)
    result = await service.get_health()
    assert result.setup_required is True
    assert result.next_step == "create_admin"


async def test_healthy_once_a_user_exists(integration_context: Context, _empty_users: None) -> None:
    ctx = integration_context
    async with ctx.admin_db.session() as session:
        user = await UserRepository.create(
            session,
            email="founder@test.local",
            first_name="Admin",
            last_name="User",
            must_change_password=False,
            invite_state=InviteState.REDEEMED,
            created_by="usr_test",
        )
        await UserSecretRepository.create(
            session,
            user_id=user.id,
            password_hash=hash_password("a-strong-passw0rd"),
            created_by="usr_test",
        )
        await session.commit()

    service = HealthService(ctx)
    result = await service.get_health()
    assert result.setup_required is False
    assert result.status == "ok"
    assert result.next_step is None
