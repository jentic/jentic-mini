"""Integration tests exercising the Postgres partial-unique dedup index directly."""

from __future__ import annotations

import datetime as dt
import os
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete

from jentic_one.control.core.schema.access_request_items import AccessRequestItem
from jentic_one.control.core.schema.access_requests import AccessRequest
from jentic_one.control.repos.access_request_repo import AccessRequestRepository
from jentic_one.shared.db.errors import DatabaseIntegrityError
from jentic_one.shared.db.session import DatabaseSession
from jentic_one.shared.models.access_requests import AccessRequestItemStatus

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("JENTIC_TEST_BACKEND", "postgres").lower() == "sqlite",
        reason="partial-unique index requires Postgres",
    ),
]

ACTOR_ID = "agent_dedup_test"


@pytest.fixture()
async def clean_access_requests(control_db: DatabaseSession) -> AsyncGenerator[None, None]:
    async with control_db.session() as session:
        await session.execute(delete(AccessRequestItem))
        await session.execute(delete(AccessRequest))
        await session.commit()
    yield
    async with control_db.session() as session:
        await session.execute(delete(AccessRequestItem))
        await session.execute(delete(AccessRequest))
        await session.commit()


async def test_duplicate_pending_items_conflict(
    control_db: DatabaseSession,
    clean_access_requests: None,
) -> None:
    """Two pending items with identical fully-specified keys hit the partial-unique index."""
    expires = dt.datetime.now(dt.UTC) + dt.timedelta(days=7)

    async with control_db.transaction() as session:
        await AccessRequestRepository.create(
            session,
            actor_id=ACTOR_ID,
            reason="first",
            requested_by="user_1",
            approve_url="",
            expires_at=expires,
            items=[
                {
                    "resource_type": "credential",
                    "action": "read",
                    "to_id": "tk_1",
                    "resource_id": "res_1",
                }
            ],
            created_by="user_1",
        )

    with pytest.raises(DatabaseIntegrityError, match="uq_access_request_items_pending_dedup"):
        async with control_db.transaction() as session:
            request = AccessRequest(
                actor_id=ACTOR_ID,
                reason="second",
                requested_by="user_1",
                approve_url="",
                expires_at=expires,
                status="pending",
                created_by="user_1",
            )
            request.items.append(
                AccessRequestItem(
                    actor_id=ACTOR_ID,
                    resource_type="credential",
                    action="read",
                    to_id="tk_1",
                    resource_id="res_1",
                    rules=[{"effect": "allow", "methods": ["GET"]}],
                    status=AccessRequestItemStatus.PENDING,
                    created_by="user_1",
                )
            )
            session.add(request)
            await session.flush()


async def test_different_status_no_conflict(
    control_db: DatabaseSession,
    clean_access_requests: None,
) -> None:
    """One pending + one approved with same keys do NOT conflict."""
    expires = dt.datetime.now(dt.UTC) + dt.timedelta(days=7)

    async with control_db.transaction() as session:
        req = await AccessRequestRepository.create(
            session,
            actor_id=ACTOR_ID,
            reason="first",
            requested_by="user_1",
            approve_url="",
            expires_at=expires,
            items=[
                {
                    "resource_type": "credential",
                    "action": "read",
                    "to_id": "tk_1",
                    "resource_id": "res_1",
                }
            ],
            created_by="user_1",
        )
        await AccessRequestRepository.decide_item(
            session,
            req.items[0].id,
            "approved",
            decided_by="reviewer_1",
        )

    async with control_db.transaction() as session:
        second = await AccessRequestRepository.create(
            session,
            actor_id=ACTOR_ID,
            reason="second",
            requested_by="user_1",
            approve_url="",
            expires_at=expires,
            items=[
                {
                    "resource_type": "credential",
                    "action": "read",
                    "to_id": "tk_1",
                    "resource_id": "res_1",
                }
            ],
            created_by="user_1",
        )
        assert second is not None
