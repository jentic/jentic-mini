"""Unit test for dedup race-condition handling in the access request service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jentic_one.control.core.errors import DuplicatePendingItemError
from jentic_one.control.services.access_requests.errors import DuplicatePendingError
from jentic_one.control.services.access_requests.service import AccessRequestService


@pytest.mark.asyncio
async def test_dedup_race_raises_duplicate_pending_error() -> None:
    ctx = MagicMock()
    ctx.config.control.access_requests.ttl_days = 7
    ctx.config.control.access_requests.canonical_base_url = "https://example.com"
    ctx.admin_db = MagicMock()
    ctx.admin_db.session = MagicMock(return_value=AsyncMock())

    tx_session = AsyncMock()
    tx_session.flush = AsyncMock()

    tx_cm = AsyncMock()
    tx_cm.__aenter__ = AsyncMock(return_value=tx_session)
    tx_cm.__aexit__ = AsyncMock(return_value=False)

    read_session = AsyncMock()
    read_cm = AsyncMock()
    read_cm.__aenter__ = AsyncMock(return_value=read_session)
    read_cm.__aexit__ = AsyncMock(return_value=False)

    ctx.control_db.transaction = MagicMock(return_value=tx_cm)
    ctx.control_db.session = MagicMock(return_value=read_cm)

    existing_item = MagicMock()
    existing_item.access_request = MagicMock()
    existing_item.access_request.approve_url = "https://example.com/access-requests/areq_exist"
    existing_item.access_request.id = "areq_exist"
    existing_item.access_request_id = "areq_exist"

    identity = MagicMock()
    identity.sub = "user_1"
    identity.parent_actor_id = None

    svc = AccessRequestService(ctx)

    with patch(
        "jentic_one.control.services.access_requests.service.AccessRequestRepository"
    ) as mock_repo:
        mock_repo.find_pending_duplicate = AsyncMock(side_effect=[None, existing_item])
        mock_repo.create = AsyncMock(side_effect=DuplicatePendingItemError())

        with pytest.raises(DuplicatePendingError) as exc_info:
            await svc.file(
                actor_id="agent_1",
                reason="test",
                items=[{"resource_type": "api", "action": "invoke"}],
                identity=identity,
            )

    assert exc_info.value.existing_request_id == "areq_exist"
    assert exc_info.value.approve_url == "https://example.com/access-requests/areq_exist"
