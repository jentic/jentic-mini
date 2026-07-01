"""Unit tests for the overlay service lifecycle operations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jentic_one.registry.services.errors import (
    ApiNotFoundError,
    OverlayNotFoundError,
    OverlayStateConflictError,
)
from jentic_one.registry.services.overlay_service import OverlayService
from jentic_one.shared.auth.identity import Identity

_IDENTITY = Identity(sub="usr_test", email="test@example.com")


def _make_ctx() -> MagicMock:
    ctx = MagicMock()
    mock_session = AsyncMock()
    ctx.registry_db.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.registry_db.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
    ctx.registry_db.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.registry_db.session.return_value.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _make_api() -> MagicMock:
    api = MagicMock()
    api.id = uuid.uuid4()
    api.vendor = "acme"
    api.name = "pets"
    api.version = "v1"
    return api


def _make_overlay(
    *, status: str = "pending", overlay_id: str = "ovr_abc123def456ghi789"
) -> MagicMock:
    overlay = MagicMock()
    overlay.id = overlay_id
    overlay.api_id = uuid.uuid4()
    overlay.status = status
    overlay.document = {"overlay": "1.0", "actions": []}
    overlay.target_revision_id = None
    overlay.contributed_by = "agent"
    overlay.confirmed_by_execution_id = None
    overlay.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    overlay.updated_at = None
    overlay.confirmed_at = None
    overlay.deprecated_at = None
    return overlay


@pytest.mark.asyncio
async def test_submit_returns_overlay_view() -> None:
    ctx = _make_ctx()
    api = _make_api()
    overlay = _make_overlay()

    with (
        patch(
            "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=api,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.create",
            new_callable=AsyncMock,
            return_value=overlay,
        ),
    ):
        svc = OverlayService(ctx)
        view = await svc.submit("acme", "pets", "v1", document={"x": 1}, identity=_IDENTITY)

    assert view.id == overlay.id
    assert view.id.startswith("ovr_")
    assert view.vendor == "acme"
    assert view.status == "pending"


@pytest.mark.asyncio
async def test_submit_api_not_found_raises_404() -> None:
    ctx = _make_ctx()

    with patch(
        "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
        new_callable=AsyncMock,
        return_value=None,
    ):
        svc = OverlayService(ctx)
        with pytest.raises(ApiNotFoundError):
            await svc.submit("acme", "missing", "v1", document={"x": 1}, identity=_IDENTITY)


@pytest.mark.asyncio
async def test_get_valid_overlay() -> None:
    ctx = _make_ctx()
    api = _make_api()
    overlay = _make_overlay()

    with (
        patch(
            "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=api,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.get_for_api",
            new_callable=AsyncMock,
            return_value=overlay,
        ),
    ):
        svc = OverlayService(ctx)
        view = await svc.get("acme", "pets", "v1", "ovr_abc123def456ghi789")

    assert view.id == overlay.id
    assert view.status == "pending"


@pytest.mark.asyncio
async def test_get_invalid_id_raises_not_found() -> None:
    ctx = _make_ctx()

    with patch(
        "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
        new_callable=AsyncMock,
        return_value=_make_api(),
    ):
        svc = OverlayService(ctx)
        with pytest.raises(OverlayNotFoundError):
            await svc.get("acme", "pets", "v1", "bad-id-no-prefix")


@pytest.mark.asyncio
async def test_get_nonexistent_overlay_raises_not_found() -> None:
    ctx = _make_ctx()
    api = _make_api()

    with (
        patch(
            "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=api,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.get_for_api",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        svc = OverlayService(ctx)
        with pytest.raises(OverlayNotFoundError):
            await svc.get("acme", "pets", "v1", "ovr_doesnotexist00000000")


@pytest.mark.asyncio
async def test_list_page_with_status_filter() -> None:
    ctx = _make_ctx()
    api = _make_api()
    overlay = _make_overlay()

    with (
        patch(
            "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=api,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.list_page",
            new_callable=AsyncMock,
            return_value=[overlay],
        ) as mock_list,
    ):
        svc = OverlayService(ctx)
        page = await svc.list_page("acme", "pets", "v1", limit=50, status="pending")

    assert len(page.data) == 1
    assert page.has_more is False
    assert page.next_cursor is None
    mock_list.assert_called_once()
    assert mock_list.call_args.kwargs["status"] == "pending"


@pytest.mark.asyncio
async def test_list_page_pagination() -> None:
    ctx = _make_ctx()
    api = _make_api()
    overlays = [_make_overlay(overlay_id=f"ovr_{i:024d}") for i in range(3)]

    with (
        patch(
            "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=api,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.list_page",
            new_callable=AsyncMock,
            return_value=overlays,
        ),
    ):
        svc = OverlayService(ctx)
        page = await svc.list_page("acme", "pets", "v1", limit=2)

    assert len(page.data) == 2
    assert page.has_more is True
    assert page.next_cursor is not None


@pytest.mark.asyncio
async def test_update_pending_succeeds() -> None:
    ctx = _make_ctx()
    api = _make_api()
    overlay = _make_overlay(status="pending")
    updated_overlay = _make_overlay(status="pending")
    updated_overlay.document = {"updated": True}

    with (
        patch(
            "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=api,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.get_for_api",
            new_callable=AsyncMock,
            side_effect=[overlay, updated_overlay],
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.update_fields",
            new_callable=AsyncMock,
            return_value=1,
        ),
    ):
        svc = OverlayService(ctx)
        view = await svc.update(
            "acme",
            "pets",
            "v1",
            "ovr_abc123def456ghi789",
            document={"updated": True},
            identity=_IDENTITY,
        )

    assert view.document == {"updated": True}


@pytest.mark.asyncio
async def test_update_confirmed_raises_conflict() -> None:
    ctx = _make_ctx()
    api = _make_api()
    overlay = _make_overlay(status="confirmed")

    with (
        patch(
            "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=api,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.get_for_api",
            new_callable=AsyncMock,
            return_value=overlay,
        ),
    ):
        svc = OverlayService(ctx)
        with pytest.raises(OverlayStateConflictError) as exc_info:
            await svc.update(
                "acme",
                "pets",
                "v1",
                "ovr_abc123def456ghi789",
                document={"x": 1},
                identity=_IDENTITY,
            )
        assert exc_info.value.action == "update"
        assert exc_info.value.current_state == "confirmed"


@pytest.mark.asyncio
async def test_confirm_pending_succeeds() -> None:
    ctx = _make_ctx()
    api = _make_api()
    overlay = _make_overlay(status="pending")
    confirmed_overlay = _make_overlay(status="confirmed")
    confirmed_overlay.confirmed_at = datetime(2024, 6, 2, tzinfo=UTC)
    confirmed_overlay.confirmed_by_execution_id = "exec-99"

    with (
        patch(
            "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=api,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.get_for_api",
            new_callable=AsyncMock,
            side_effect=[overlay, confirmed_overlay],
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.set_status",
            new_callable=AsyncMock,
            return_value=1,
        ),
    ):
        svc = OverlayService(ctx)
        view = await svc.confirm(
            "acme",
            "pets",
            "v1",
            "ovr_abc123def456ghi789",
            execution_id="exec-99",
            identity=_IDENTITY,
        )

    assert view.status == "confirmed"
    assert view.confirmed_by_execution_id == "exec-99"


@pytest.mark.asyncio
async def test_confirm_already_confirmed_is_idempotent() -> None:
    ctx = _make_ctx()
    api = _make_api()
    overlay = _make_overlay(status="confirmed")
    overlay.confirmed_at = datetime(2024, 6, 2, tzinfo=UTC)

    with (
        patch(
            "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=api,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.get_for_api",
            new_callable=AsyncMock,
            return_value=overlay,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.set_status",
            new_callable=AsyncMock,
        ) as mock_set_status,
    ):
        svc = OverlayService(ctx)
        view = await svc.confirm("acme", "pets", "v1", "ovr_abc123def456ghi789", identity=_IDENTITY)

    assert view.status == "confirmed"
    mock_set_status.assert_not_called()


@pytest.mark.asyncio
async def test_confirm_deprecated_raises_conflict() -> None:
    ctx = _make_ctx()
    api = _make_api()
    overlay = _make_overlay(status="deprecated")

    with (
        patch(
            "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=api,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.get_for_api",
            new_callable=AsyncMock,
            return_value=overlay,
        ),
    ):
        svc = OverlayService(ctx)
        with pytest.raises(OverlayStateConflictError) as exc_info:
            await svc.confirm("acme", "pets", "v1", "ovr_abc123def456ghi789", identity=_IDENTITY)
        assert exc_info.value.action == "confirm"


@pytest.mark.asyncio
async def test_deprecate_sets_status() -> None:
    ctx = _make_ctx()
    api = _make_api()
    overlay = _make_overlay(status="pending")

    with (
        patch(
            "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=api,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.get_for_api",
            new_callable=AsyncMock,
            return_value=overlay,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.set_status",
            new_callable=AsyncMock,
            return_value=1,
        ) as mock_set_status,
    ):
        svc = OverlayService(ctx)
        await svc.deprecate("acme", "pets", "v1", "ovr_abc123def456ghi789", identity=_IDENTITY)

    mock_set_status.assert_called_once()
    assert mock_set_status.call_args.args[1] == "ovr_abc123def456ghi789"
    assert mock_set_status.call_args.args[2] == "deprecated"


@pytest.mark.asyncio
async def test_deprecate_nonexistent_raises_not_found() -> None:
    ctx = _make_ctx()
    api = _make_api()

    with (
        patch(
            "jentic_one.registry.services.overlay_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=api,
        ),
        patch(
            "jentic_one.registry.services.overlay_service.OverlayRepository.get_for_api",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        svc = OverlayService(ctx)
        with pytest.raises(OverlayNotFoundError):
            await svc.deprecate(
                "acme", "pets", "v1", "ovr_doesnotexist00000000", identity=_IDENTITY
            )
