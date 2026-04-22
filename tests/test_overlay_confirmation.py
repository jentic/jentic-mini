"""Overlay confirmation tests — verify pending overlays transition to confirmed.

The broker calls confirm_overlay() after a successful upstream response.
These tests exercise the function directly since we can't get a < 400
response from non-routable test hosts.
"""

import asyncio
import json
import os
import uuid

import aiosqlite
import pytest
from src.routers.overlays import confirm_overlay


@pytest.fixture(scope="module")
def test_api(client, admin_session):
    """Register a test API and return its api_id."""
    api_id = "overlay-test.example.com"

    async def setup():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO apis (id, name, base_url) VALUES (?, ?, ?)",
                (api_id, "Overlay Test API", f"https://{api_id}"),
            )
            await db.commit()

    asyncio.run(setup())
    return api_id


def test_confirm_overlay_transitions_pending_to_confirmed(client, admin_session, test_api):
    """A pending overlay should transition to confirmed when confirm_overlay is called."""

    async def run():
        db_path = os.environ["DB_PATH"]
        overlay_id = f"test-overlay-{uuid.uuid4().hex[:8]}"
        execution_id = f"exec-{uuid.uuid4().hex[:8]}"
        overlay_doc = json.dumps(
            {
                "actions": [
                    {
                        "target": "$",
                        "update": {
                            "components": {
                                "securitySchemes": {
                                    "BearerAuth": {"type": "http", "scheme": "bearer"}
                                }
                            }
                        },
                    }
                ]
            }
        )

        # Insert a pending overlay
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT INTO api_overlays (id, api_id, overlay, status) VALUES (?, ?, ?, 'pending')",
                (overlay_id, test_api, overlay_doc),
            )
            await db.commit()

        # Confirm it
        await confirm_overlay(test_api, execution_id)

        # Verify it's confirmed
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT status, confirmed_by_execution FROM api_overlays WHERE id=?",
                (overlay_id,),
            ) as cur:
                row = await cur.fetchone()

        assert row is not None, "Overlay not found"
        assert row[0] == "confirmed", f"Expected status 'confirmed', got '{row[0]}'"
        assert row[1] == execution_id, f"Expected execution_id '{execution_id}', got '{row[1]}'"

    asyncio.run(run())


def test_confirm_overlay_skips_when_no_pending(client, admin_session, test_api):
    """confirm_overlay should be a no-op when no pending overlays exist."""

    async def run():
        db_path = os.environ["DB_PATH"]
        # Insert a confirmed overlay (not pending)
        overlay_id = f"test-confirmed-{uuid.uuid4().hex[:8]}"
        overlay_doc = json.dumps({"actions": []})

        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT INTO api_overlays (id, api_id, overlay, status) VALUES (?, ?, ?, 'confirmed')",
                (overlay_id, test_api, overlay_doc),
            )
            await db.commit()

        # Call confirm — should not error, should not change anything
        await confirm_overlay(test_api, "exec-noop")

        # Verify the confirmed overlay is unchanged
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT confirmed_by_execution FROM api_overlays WHERE id=?",
                (overlay_id,),
            ) as cur:
                row = await cur.fetchone()

        assert row[0] is None or row[0] != "exec-noop", (
            "Should not have updated the already-confirmed overlay"
        )

    asyncio.run(run())


def test_confirm_overlay_only_confirms_first_pending(client, admin_session, test_api):
    """When multiple pending overlays exist, only the oldest should be confirmed."""

    async def run():
        db_path = os.environ["DB_PATH"]
        overlay_1 = f"test-first-{uuid.uuid4().hex[:8]}"
        overlay_2 = f"test-second-{uuid.uuid4().hex[:8]}"
        overlay_doc = json.dumps({"actions": []})

        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT INTO api_overlays (id, api_id, overlay, status, created_at) VALUES (?, ?, ?, 'pending', 1000)",
                (overlay_1, test_api, overlay_doc),
            )
            await db.execute(
                "INSERT INTO api_overlays (id, api_id, overlay, status, created_at) VALUES (?, ?, ?, 'pending', 2000)",
                (overlay_2, test_api, overlay_doc),
            )
            await db.commit()

        await confirm_overlay(test_api, "exec-first-only")

        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT status FROM api_overlays WHERE id=?", (overlay_1,)
            ) as cur:
                row1 = await cur.fetchone()
            async with db.execute(
                "SELECT status FROM api_overlays WHERE id=?", (overlay_2,)
            ) as cur:
                row2 = await cur.fetchone()

        assert row1[0] == "confirmed", f"First overlay should be confirmed, got '{row1[0]}'"
        assert row2[0] == "pending", f"Second overlay should still be pending, got '{row2[0]}'"

    asyncio.run(run())
