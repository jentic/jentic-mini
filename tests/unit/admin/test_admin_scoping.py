"""Unit tests for admin-surface dynamic query scoping."""

from __future__ import annotations

import pytest

from jentic_one.admin.core.schema.agents import Agent
from jentic_one.admin.core.schema.service_accounts import ServiceAccount
from jentic_one.admin.core.schema.users import User
from jentic_one.admin.scoping.filters import build_access_filters
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.models import ActorType
from jentic_one.shared.scopes import OWNER_AGENTS_READ, OWNER_SERVICE_ACCOUNTS_READ


def _identity(
    sub: str = "user_1",
    permissions: list[str] | None = None,
    actor_type: ActorType = ActorType.USER,
    parent_actor_id: str | None = None,
) -> Identity:
    return Identity(
        sub=sub,
        email="test@example.com",
        permissions=permissions or [],
        actor_type=actor_type,
        parent_actor_id=parent_actor_id,
    )


def test_admin_identity_returns_empty_filters() -> None:
    identity = _identity(permissions=["org:admin"])
    filters = build_access_filters(identity, Agent)
    assert filters == []


def test_user_identity_returns_owner_filter() -> None:
    identity = _identity(sub="user_42", permissions=["agents:read"])
    filters = build_access_filters(identity, Agent)
    assert len(filters) == 1
    compiled = filters[0].compile(compile_kwargs={"literal_binds": True})
    sql = str(compiled)
    assert "user_42" in sql
    assert "owner_id" in sql


def test_empty_sub_raises_value_error() -> None:
    identity = _identity(sub="", permissions=[])
    with pytest.raises(ValueError, match="empty sub"):
        build_access_filters(identity, Agent)


def test_unknown_model_raises_value_error() -> None:
    identity = _identity(sub="user_1", permissions=[])

    class FakeModel:
        pass

    with pytest.raises(ValueError, match="Unknown model"):
        build_access_filters(identity, FakeModel)


def test_agent_with_delegation_scope_returns_or_filter() -> None:
    identity = _identity(
        sub="agent_1",
        permissions=[OWNER_AGENTS_READ],
        actor_type=ActorType.AGENT,
        parent_actor_id="user_owner",
    )
    filters = build_access_filters(identity, Agent)
    assert len(filters) == 1
    compiled = filters[0].compile(compile_kwargs={"literal_binds": True})
    sql = str(compiled)
    assert "agent_1" in sql
    assert "user_owner" in sql


def test_agent_without_delegation_scope_returns_single_filter() -> None:
    identity = _identity(
        sub="agent_1",
        permissions=["agents:read"],
        actor_type=ActorType.AGENT,
        parent_actor_id="user_owner",
    )
    filters = build_access_filters(identity, Agent)
    assert len(filters) == 1
    compiled = filters[0].compile(compile_kwargs={"literal_binds": True})
    sql = str(compiled)
    assert "agent_1" in sql
    assert "user_owner" not in sql


def test_agent_with_scope_but_no_parent_returns_single_filter() -> None:
    identity = _identity(
        sub="agent_1",
        permissions=[OWNER_AGENTS_READ],
        actor_type=ActorType.AGENT,
        parent_actor_id=None,
    )
    filters = build_access_filters(identity, Agent)
    assert len(filters) == 1
    compiled = filters[0].compile(compile_kwargs={"literal_binds": True})
    sql = str(compiled)
    assert "agent_1" in sql


def test_service_account_model_returns_owner_filter() -> None:
    identity = _identity(sub="user_7", permissions=[])
    filters = build_access_filters(identity, ServiceAccount)
    assert len(filters) == 1
    compiled = filters[0].compile(compile_kwargs={"literal_binds": True})
    sql = str(compiled)
    assert "user_7" in sql
    assert "owner_id" in sql


def test_service_account_with_delegation_scope() -> None:
    identity = _identity(
        sub="agent_x",
        permissions=[OWNER_SERVICE_ACCOUNTS_READ],
        actor_type=ActorType.AGENT,
        parent_actor_id="user_delegator",
    )
    filters = build_access_filters(identity, ServiceAccount)
    assert len(filters) == 1
    compiled = filters[0].compile(compile_kwargs={"literal_binds": True})
    sql = str(compiled)
    assert "agent_x" in sql
    assert "user_delegator" in sql


def test_user_model_returns_self_scope_filter() -> None:
    identity = _identity(sub="usr_self", permissions=[])
    filters = build_access_filters(identity, User)
    assert len(filters) == 1
    compiled = filters[0].compile(compile_kwargs={"literal_binds": True})
    sql = str(compiled)
    assert "usr_self" in sql
