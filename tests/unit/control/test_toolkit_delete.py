"""Unit tests for toolkit hard-delete with cascade."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jentic_one.control.services.toolkits.errors import ToolkitNotFoundError
from jentic_one.control.services.toolkits.service import ToolkitService
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.models import ActorType
from jentic_one.shared.models.audit import AuditAction, AuditTargetType

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
    control_session = AsyncMock()
    ctx.control_db.transaction.return_value.__aenter__ = AsyncMock(return_value=control_session)
    ctx.control_db.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
    admin_session = AsyncMock()
    ctx.admin_db.transaction.return_value.__aenter__ = AsyncMock(return_value=admin_session)
    ctx.admin_db.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _make_toolkit(toolkit_id: str = "tk_abc123") -> MagicMock:
    toolkit = MagicMock()
    toolkit.id = toolkit_id
    toolkit.name = "Test Toolkit"
    toolkit.active = True
    return toolkit


@pytest.mark.asyncio
@patch(f"{_SVC_MODULE}.record_audit_best_effort", new_callable=AsyncMock)
@patch(f"{_SVC_MODULE}.PrerequisiteRepository")
@patch(f"{_SVC_MODULE}.ToolkitRepository")
@patch(f"{_SVC_MODULE}.build_access_filters")
async def test_delete_existing_toolkit(
    mock_filters: MagicMock,
    mock_repo: MagicMock,
    mock_prereq: MagicMock,
    mock_audit: AsyncMock,
) -> None:
    mock_filters.return_value = []
    mock_repo.get_by_id = AsyncMock(return_value=_make_toolkit())
    mock_repo.delete = AsyncMock(return_value=True)
    mock_prereq.delete_agent_toolkit_bindings_for_toolkit = AsyncMock(return_value=0)

    ctx = _make_ctx()
    svc = ToolkitService(ctx)
    await svc.delete("tk_abc123", identity=_identity())

    mock_repo.delete.assert_called_once()
    mock_prereq.delete_agent_toolkit_bindings_for_toolkit.assert_called_once()


@pytest.mark.asyncio
@patch(f"{_SVC_MODULE}.record_audit_best_effort", new_callable=AsyncMock)
@patch(f"{_SVC_MODULE}.PrerequisiteRepository")
@patch(f"{_SVC_MODULE}.ToolkitRepository")
@patch(f"{_SVC_MODULE}.build_access_filters")
async def test_delete_nonexistent_toolkit_raises(
    mock_filters: MagicMock,
    mock_repo: MagicMock,
    mock_prereq: MagicMock,
    mock_audit: AsyncMock,
) -> None:
    mock_filters.return_value = []
    mock_repo.get_by_id = AsyncMock(return_value=None)

    ctx = _make_ctx()
    svc = ToolkitService(ctx)

    with pytest.raises(ToolkitNotFoundError):
        await svc.delete("tk_nonexistent", identity=_identity())

    mock_repo.delete.assert_not_called()
    mock_prereq.delete_agent_toolkit_bindings_for_toolkit.assert_not_called()


@pytest.mark.asyncio
@patch(f"{_SVC_MODULE}.record_audit_best_effort", new_callable=AsyncMock)
@patch(f"{_SVC_MODULE}.PrerequisiteRepository")
@patch(f"{_SVC_MODULE}.ToolkitRepository")
@patch(f"{_SVC_MODULE}.build_access_filters")
async def test_delete_removes_agent_bindings(
    mock_filters: MagicMock,
    mock_repo: MagicMock,
    mock_prereq: MagicMock,
    mock_audit: AsyncMock,
) -> None:
    mock_filters.return_value = []
    mock_repo.get_by_id = AsyncMock(return_value=_make_toolkit("tk_with_bindings"))
    mock_repo.delete = AsyncMock(return_value=True)
    mock_prereq.delete_agent_toolkit_bindings_for_toolkit = AsyncMock(return_value=3)

    ctx = _make_ctx()
    svc = ToolkitService(ctx)
    await svc.delete("tk_with_bindings", identity=_identity())

    mock_prereq.delete_agent_toolkit_bindings_for_toolkit.assert_called_once()
    call_kwargs = mock_prereq.delete_agent_toolkit_bindings_for_toolkit.call_args[1]
    assert call_kwargs["toolkit_id"] == "tk_with_bindings"


@pytest.mark.asyncio
@patch(f"{_SVC_MODULE}.record_audit_best_effort", new_callable=AsyncMock)
@patch(f"{_SVC_MODULE}.PrerequisiteRepository")
@patch(f"{_SVC_MODULE}.ToolkitRepository")
@patch(f"{_SVC_MODULE}.build_access_filters")
async def test_delete_non_owner_raises_not_found(
    mock_filters: MagicMock,
    mock_repo: MagicMock,
    mock_prereq: MagicMock,
    mock_audit: AsyncMock,
) -> None:
    mock_filters.return_value = ["some_filter"]
    mock_repo.get_by_id = AsyncMock(return_value=None)

    ctx = _make_ctx()
    svc = ToolkitService(ctx)
    non_owner = Identity(
        sub="other_user",
        email="other@example.com",
        permissions=["toolkits:write"],
        actor_type=ActorType.USER,
        parent_actor_id=None,
    )

    with pytest.raises(ToolkitNotFoundError):
        await svc.delete("tk_abc123", identity=non_owner)

    mock_repo.delete.assert_not_called()
    mock_audit.assert_not_called()


@pytest.mark.asyncio
@patch(f"{_SVC_MODULE}.record_audit_best_effort", new_callable=AsyncMock)
@patch(f"{_SVC_MODULE}.PrerequisiteRepository")
@patch(f"{_SVC_MODULE}.ToolkitRepository")
@patch(f"{_SVC_MODULE}.build_access_filters")
async def test_delete_emits_audit_entry(
    mock_filters: MagicMock,
    mock_repo: MagicMock,
    mock_prereq: MagicMock,
    mock_audit: AsyncMock,
) -> None:
    mock_filters.return_value = []
    mock_repo.get_by_id = AsyncMock(return_value=_make_toolkit())
    mock_repo.delete = AsyncMock(return_value=True)
    mock_prereq.delete_agent_toolkit_bindings_for_toolkit = AsyncMock(return_value=0)

    ctx = _make_ctx()
    svc = ToolkitService(ctx)
    identity = _identity(sub="user_42")
    await svc.delete("tk_abc123", identity=identity)

    mock_audit.assert_called_once_with(
        ctx,
        action=AuditAction.DELETE,
        target_type=AuditTargetType.TOOLKIT,
        target_id="tk_abc123",
        actor_type=ActorType.USER,
        actor_id="user_42",
        origin="api",
    )
