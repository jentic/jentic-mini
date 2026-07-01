"""Unit tests for ApiKeyResolver."""

from __future__ import annotations

from collections import namedtuple
from unittest.mock import AsyncMock, MagicMock

import pytest

from jentic_one.shared.auth.api_key_resolver import ApiKeyResolver
from jentic_one.shared.models import ActorType

Row = namedtuple("Row", ["scope"])
AgentRow = namedtuple("AgentRow", ["agent_id", "status", "owner_id"])
SARow = namedtuple("SARow", ["service_account_id", "status"])


@pytest.fixture()
def admin_db() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def resolver(admin_db: MagicMock) -> ApiKeyResolver:
    return ApiKeyResolver(admin_db)


@pytest.mark.asyncio
async def test_resolve_agent_key_active(resolver: ApiKeyResolver, admin_db: MagicMock) -> None:
    agent_row = AgentRow(agent_id="agnt_123", status="active", owner_id="usr_owner")
    scope_rows = [Row(scope="broker:execute"), Row(scope="toolkit:read")]

    session_mock = AsyncMock()
    call_count = 0

    async def _execute(stmt: object, params: dict[str, object]) -> object:
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.one_or_none.return_value = agent_row
        else:
            result.all.return_value = scope_rows
        return result

    session_mock.execute = _execute
    ctx_mgr = AsyncMock()
    ctx_mgr.__aenter__.return_value = session_mock
    ctx_mgr.__aexit__.return_value = None
    admin_db.session.return_value = ctx_mgr

    identity = await resolver.resolve("jak_test_secret_value")

    assert identity is not None
    assert identity.sub == "agnt_123"
    assert identity.actor_type == ActorType.AGENT
    assert identity.parent_actor_id == "usr_owner"
    assert identity.active is True
    assert "broker:execute" in identity.permissions
    assert "toolkit:read" in identity.permissions


@pytest.mark.asyncio
async def test_resolve_service_account_key_active(
    resolver: ApiKeyResolver, admin_db: MagicMock
) -> None:
    sa_row = SARow(service_account_id="sva_456", status="active")
    scope_rows = [Row(scope="broker:execute")]

    session_mock = AsyncMock()
    call_count = 0

    async def _execute(stmt: object, params: dict[str, object]) -> object:
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.one_or_none.return_value = sa_row
        else:
            result.all.return_value = scope_rows
        return result

    session_mock.execute = _execute
    ctx_mgr = AsyncMock()
    ctx_mgr.__aenter__.return_value = session_mock
    ctx_mgr.__aexit__.return_value = None
    admin_db.session.return_value = ctx_mgr

    identity = await resolver.resolve("sak_test_secret_value")

    assert identity is not None
    assert identity.sub == "sva_456"
    assert identity.actor_type == ActorType.SERVICE_ACCOUNT
    assert identity.active is True
    assert "broker:execute" in identity.permissions


@pytest.mark.asyncio
async def test_resolve_agent_key_inactive(resolver: ApiKeyResolver, admin_db: MagicMock) -> None:
    agent_row = AgentRow(agent_id="agnt_123", status="disabled", owner_id="usr_owner")

    session_mock = AsyncMock()

    async def _execute(stmt: object, params: dict[str, object]) -> object:
        result = MagicMock()
        result.one_or_none.return_value = agent_row
        return result

    session_mock.execute = _execute
    ctx_mgr = AsyncMock()
    ctx_mgr.__aenter__.return_value = session_mock
    ctx_mgr.__aexit__.return_value = None
    admin_db.session.return_value = ctx_mgr

    identity = await resolver.resolve("jak_disabled_agent")
    assert identity is None


@pytest.mark.asyncio
async def test_resolve_key_not_found(resolver: ApiKeyResolver, admin_db: MagicMock) -> None:
    session_mock = AsyncMock()

    async def _execute(stmt: object, params: dict[str, object]) -> object:
        result = MagicMock()
        result.one_or_none.return_value = None
        return result

    session_mock.execute = _execute
    ctx_mgr = AsyncMock()
    ctx_mgr.__aenter__.return_value = session_mock
    ctx_mgr.__aexit__.return_value = None
    admin_db.session.return_value = ctx_mgr

    identity = await resolver.resolve("jak_nonexistent_key")
    assert identity is None


@pytest.mark.asyncio
async def test_resolve_unknown_prefix(resolver: ApiKeyResolver) -> None:
    identity = await resolver.resolve("unknown_prefix_key")
    assert identity is None


@pytest.mark.asyncio
async def test_resolve_access_token_protocol(resolver: ApiKeyResolver, admin_db: MagicMock) -> None:
    """Verify resolve_access_token delegates to resolve (TokenResolverProtocol)."""
    session_mock = AsyncMock()

    async def _execute(stmt: object, params: dict[str, object]) -> object:
        result = MagicMock()
        result.one_or_none.return_value = None
        return result

    session_mock.execute = _execute
    ctx_mgr = AsyncMock()
    ctx_mgr.__aenter__.return_value = session_mock
    ctx_mgr.__aexit__.return_value = None
    admin_db.session.return_value = ctx_mgr

    identity = await resolver.resolve_access_token("jak_proto_test")
    assert identity is None
