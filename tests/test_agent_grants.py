"""Grant audit + disabled-toolkit visibility regressions.

Two related guarantees:

* Re-granting a toolkit must not clobber the original ``granted_at`` /
  ``granted_by`` audit fields. The first row to win owns the audit trail.
* ``GET /agents/{id}/grants`` must surface the toolkit's ``disabled`` flag so
  the admin UI can warn that a granted toolkit no longer takes effect at
  runtime (the auth layer already filters disabled toolkits out, but the row
  in ``agent_toolkit_grants`` lingers).
"""

from __future__ import annotations

import json
import time

import aiosqlite
import pytest
from src.db import DB_PATH


async def _seed_toolkit(toolkit_id: str, *, disabled: bool = False) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO toolkits (id, name, api_key, disabled) VALUES (?, ?, ?, ?)",
            (toolkit_id, toolkit_id, f"api_{toolkit_id}", 1 if disabled else 0),
        )
        await db.commit()


async def _seed_approved_agent(client_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO agents (client_id, client_name, status, jwks_json, created_at)
               VALUES (?, ?, 'approved', ?, strftime('%s','now'))""",
            (client_id, f"test-{client_id}", json.dumps({"keys": []})),
        )
        await db.commit()


async def _cleanup(client_id: str, *toolkit_ids: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM agent_toolkit_grants WHERE client_id=?", (client_id,))
        await db.execute("DELETE FROM agents WHERE client_id=?", (client_id,))
        for tid in toolkit_ids:
            # Don't delete `default` — other tests rely on it.
            if tid != "default":
                await db.execute("DELETE FROM toolkits WHERE id=?", (tid,))
        await db.commit()


@pytest.mark.asyncio
async def test_regrant_preserves_original_audit(admin_client):
    """Re-granting the same toolkit must not overwrite ``granted_at`` /
    ``granted_by`` — the first grant owns the audit record.
    """
    cid = "agnt_regrant_audit_aaaaaaaaaa"
    tid = "tk_regrant_audit"
    await _seed_approved_agent(cid)
    await _seed_toolkit(tid)

    try:
        r1 = admin_client.post(f"/agents/{cid}/grants", json={"toolkit_id": tid})
        assert r1.status_code == 200, r1.text
        body1 = r1.json()
        first_granted_at = body1["granted_at"]
        assert body1["created"] is True, "first POST should report a fresh insert"

        # Read back the persisted row so we know exactly what was stored,
        # not just what the response echoed.
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT granted_at, granted_by FROM agent_toolkit_grants "
                "WHERE client_id=? AND toolkit_id=?",
                (cid, tid),
            ) as cur:
                original = await cur.fetchone()
        assert original["granted_by"] is not None

        # Sleep a beat so any timestamp overwrite would be detectable.
        time.sleep(0.05)

        r2 = admin_client.post(f"/agents/{cid}/grants", json={"toolkit_id": tid})
        assert r2.status_code == 200, r2.text
        body2 = r2.json()

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT granted_at, granted_by FROM agent_toolkit_grants "
                "WHERE client_id=? AND toolkit_id=?",
                (cid, tid),
            ) as cur:
                after = await cur.fetchone()

        assert after["granted_at"] == original["granted_at"], (
            "regrant clobbered granted_at — audit trail lost"
        )
        assert after["granted_by"] == original["granted_by"], (
            "regrant clobbered granted_by — audit trail lost"
        )
        # The response now mirrors the persisted row (not `now`) and flags
        # the no-op via `created`. Callers can safely trust either side.
        assert body2["created"] is False, "regrant should report a no-op insert"
        assert body2["granted_at"] == first_granted_at, (
            "regrant response should echo the original granted_at, not now"
        )
        assert body2["granted_by"] == body1["granted_by"]
    finally:
        await _cleanup(cid, tid)


@pytest.mark.asyncio
async def test_list_grants_surfaces_disabled_flag(admin_client):
    """``GET /agents/{id}/grants`` must report each toolkit's disabled state."""
    cid = "agnt_grants_disabled_aaaaaaa"
    tid_active = "tk_grants_disabled_active"
    tid_disabled = "tk_grants_disabled_disabled"
    await _seed_approved_agent(cid)
    await _seed_toolkit(tid_active, disabled=False)
    await _seed_toolkit(tid_disabled, disabled=False)

    try:
        # Grant both while they're active — add_grant rejects disabled toolkits
        # (B17 by another name), so the only way to end up with a "grant on a
        # disabled toolkit" is to disable the toolkit *after* granting.
        for tid in (tid_active, tid_disabled):
            r = admin_client.post(f"/agents/{cid}/grants", json={"toolkit_id": tid})
            assert r.status_code == 200, r.text

        # Now disable one of them.
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE toolkits SET disabled=1 WHERE id=?", (tid_disabled,))
            await db.commit()

        r = admin_client.get(f"/agents/{cid}/grants")
        assert r.status_code == 200, r.text
        grants = {g["toolkit_id"]: g for g in r.json()["grants"]}

        assert grants[tid_active]["disabled"] is False
        assert grants[tid_disabled]["disabled"] is True
        # Audit fields still present.
        for g in grants.values():
            assert "granted_at" in g
            assert "granted_by" in g
    finally:
        await _cleanup(cid, tid_active, tid_disabled)


@pytest.mark.asyncio
async def test_grant_disabled_toolkit_rejected(admin_client):
    """The handler still refuses to grant a *currently*-disabled toolkit at
    creation time — this is the fast path; the disabled-flag surfacing above
    only matters once a toolkit gets disabled after the grant exists.
    """
    cid = "agnt_grants_reject_aaaaaaaaa"
    tid = "tk_grants_reject_disabled"
    await _seed_approved_agent(cid)
    await _seed_toolkit(tid, disabled=True)

    try:
        r = admin_client.post(f"/agents/{cid}/grants", json={"toolkit_id": tid})
        assert r.status_code == 409
        assert "disabled" in r.json()["detail"].lower()
    finally:
        await _cleanup(cid, tid)
