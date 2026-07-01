"""Unit tests for toolkit list_bindings returning permissions."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jentic_one.control.core.schema.toolkit_credential_bindings import ToolkitCredentialBinding
from jentic_one.control.core.schema.toolkit_permission_rules import ToolkitPermissionRule
from jentic_one.control.services.toolkits.service import ToolkitService
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.models import ActorType

_SVC_MODULE = "jentic_one.control.services.toolkits.service"


def _identity(sub: str = "user_1") -> Identity:
    return Identity(
        sub=sub,
        email="test@example.com",
        permissions=["org:admin"],
        actor_type=ActorType.USER,
        parent_actor_id=None,
    )


def _make_ctx() -> MagicMock:
    ctx = MagicMock()
    session = AsyncMock()
    ctx.control_db.session.return_value.__aenter__ = AsyncMock(return_value=session)
    ctx.control_db.session.return_value.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _make_toolkit(toolkit_id: str = "tk_abc123") -> MagicMock:
    toolkit = MagicMock()
    toolkit.id = toolkit_id
    return toolkit


def _make_binding(toolkit_id: str, credential_id: str) -> MagicMock:
    binding = MagicMock(spec=ToolkitCredentialBinding)
    binding.toolkit_id = toolkit_id
    binding.credential_id = credential_id
    binding.bound_at = datetime(2024, 1, 1, tzinfo=UTC)
    return binding


def _make_rule(effect: str = "allow", path: str = "/api/*") -> MagicMock:
    rule = MagicMock(spec=ToolkitPermissionRule)
    rule.effect = effect
    rule.path = path
    rule.methods = ["GET"]
    rule.operations = None
    rule.is_system = False
    rule.comment = None
    return rule


@pytest.mark.asyncio
@patch(f"{_SVC_MODULE}.ToolkitPermissionRepository")
@patch(f"{_SVC_MODULE}.ToolkitBindingRepository")
@patch(f"{_SVC_MODULE}.ToolkitRepository")
@patch(f"{_SVC_MODULE}.build_access_filters")
async def test_list_bindings_returns_permissions(
    mock_filters: MagicMock,
    mock_toolkit_repo: MagicMock,
    mock_binding_repo: MagicMock,
    mock_perm_repo: MagicMock,
) -> None:
    """list_bindings should include permission rules for each binding."""
    mock_filters.return_value = []
    mock_toolkit_repo.get_by_id = AsyncMock(return_value=_make_toolkit())

    binding = _make_binding("tk_abc123", "cred_001")
    mock_binding_repo.list_by_toolkit = AsyncMock(return_value=[binding])

    rule = _make_rule(effect="allow", path="/api/v1/*")
    mock_perm_repo.list_rules = AsyncMock(return_value=[rule])

    ctx = _make_ctx()
    svc = ToolkitService(ctx)
    page = await svc.list_bindings("tk_abc123", identity=_identity())

    assert len(page.data) == 1
    assert page.data[0].binding is binding
    assert page.data[0].rules == [rule]
    assert page.has_more is False
    assert page.next_cursor is None
    mock_perm_repo.list_rules.assert_called_once()
    call_args = mock_perm_repo.list_rules.call_args[0]
    assert call_args[1] == "tk_abc123"
    assert call_args[2] == "cred_001"


@pytest.mark.asyncio
@patch(f"{_SVC_MODULE}.ToolkitPermissionRepository")
@patch(f"{_SVC_MODULE}.ToolkitBindingRepository")
@patch(f"{_SVC_MODULE}.ToolkitRepository")
@patch(f"{_SVC_MODULE}.build_access_filters")
async def test_list_bindings_multiple_bindings_each_gets_rules(
    mock_filters: MagicMock,
    mock_toolkit_repo: MagicMock,
    mock_binding_repo: MagicMock,
    mock_perm_repo: MagicMock,
) -> None:
    """Each binding in the list should have its own permission rules loaded."""
    mock_filters.return_value = []
    mock_toolkit_repo.get_by_id = AsyncMock(return_value=_make_toolkit())

    binding1 = _make_binding("tk_abc123", "cred_001")
    binding2 = _make_binding("tk_abc123", "cred_002")
    mock_binding_repo.list_by_toolkit = AsyncMock(return_value=[binding1, binding2])

    rule1 = _make_rule(effect="allow", path="/api/v1/*")
    rule2 = _make_rule(effect="deny", path="/admin/*")

    async def fake_list_rules(_session: object, _tk_id: str, cred_id: str) -> list[MagicMock]:
        if cred_id == "cred_001":
            return [rule1]
        return [rule2]

    mock_perm_repo.list_rules = AsyncMock(side_effect=fake_list_rules)

    ctx = _make_ctx()
    svc = ToolkitService(ctx)
    page = await svc.list_bindings("tk_abc123", identity=_identity())

    assert len(page.data) == 2
    assert page.data[0].rules == [rule1]
    assert page.data[1].rules == [rule2]


@pytest.mark.asyncio
@patch(f"{_SVC_MODULE}.ToolkitPermissionRepository")
@patch(f"{_SVC_MODULE}.ToolkitBindingRepository")
@patch(f"{_SVC_MODULE}.ToolkitRepository")
@patch(f"{_SVC_MODULE}.build_access_filters")
async def test_list_bindings_empty_permissions(
    mock_filters: MagicMock,
    mock_toolkit_repo: MagicMock,
    mock_binding_repo: MagicMock,
    mock_perm_repo: MagicMock,
) -> None:
    """A binding with no rules should still return an empty rules list."""
    mock_filters.return_value = []
    mock_toolkit_repo.get_by_id = AsyncMock(return_value=_make_toolkit())

    binding = _make_binding("tk_abc123", "cred_001")
    mock_binding_repo.list_by_toolkit = AsyncMock(return_value=[binding])
    mock_perm_repo.list_rules = AsyncMock(return_value=[])

    ctx = _make_ctx()
    svc = ToolkitService(ctx)
    page = await svc.list_bindings("tk_abc123", identity=_identity())

    assert len(page.data) == 1
    assert page.data[0].rules == []
