"""``PUT /agents/{id}/grants`` — atomic full-replace.

The frontend used to apply grant changes by dispatching one POST per add and
one DELETE per remove, sequentially. A 5xx mid-stream left the agent in a
half-applied state that the UI's confirm dialog had no way to reconcile —
a real audit-trail problem on a security-sensitive surface. This endpoint
collapses the whole thing into a single transaction.
"""

from __future__ import annotations

import asyncio
import json
import time

import aiosqlite
import pytest
from src.db import DB_PATH


async def _seed_agent(client_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO agents (client_id, client_name, status, jwks_json, created_at)
               VALUES (?, ?, 'approved', ?, ?)""",
            (client_id, f"test-{client_id}", json.dumps({"keys": []}), time.time()),
        )
        await db.commit()


async def _seed_toolkit(toolkit_id: str, *, disabled: bool = False) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO toolkits (id, name, api_key, disabled) VALUES (?, ?, ?, ?)",
            (toolkit_id, toolkit_id, f"api_{toolkit_id}", 1 if disabled else 0),
        )
        await db.commit()


async def _read_grants(client_id: str) -> dict[str, dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT toolkit_id, granted_at, granted_by FROM agent_toolkit_grants "
            "WHERE client_id=? ORDER BY granted_at",
            (client_id,),
        ) as cur:
            return {r["toolkit_id"]: dict(r) for r in await cur.fetchall()}


async def _cleanup(client_id: str, *toolkit_ids: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM agent_toolkit_grants WHERE client_id=?", (client_id,))
        await db.execute("DELETE FROM agents WHERE client_id=?", (client_id,))
        for tid in toolkit_ids:
            if tid != "default":
                await db.execute("DELETE FROM toolkits WHERE id=?", (tid,))
        await db.commit()


@pytest.mark.asyncio
async def test_replace_grants_adds_and_removes_atomically(admin_client):
    cid = "agnt_put_grants_basic_aaaaaaa"
    a, b, c = "tk_put_basic_a", "tk_put_basic_b", "tk_put_basic_c"
    await _seed_agent(cid)
    for tid in (a, b, c):
        await _seed_toolkit(tid)

    try:
        # Pre-grant a + b via POST so we can prove the PUT removes b and adds c.
        for tid in (a, b):
            r = admin_client.post(f"/agents/{cid}/grants", json={"toolkit_id": tid})
            assert r.status_code == 200, r.text
        before = await _read_grants(cid)
        assert set(before) == {a, b}
        a_original_at = before[a]["granted_at"]

        # Sleep so any clobber-on-PUT would be detectable.
        await asyncio.sleep(0.05)

        r = admin_client.put(
            f"/agents/{cid}/grants",
            json={"toolkit_ids": [a, c]},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body["added"]) == {c}
        assert set(body["removed"]) == {b}
        assert set(body["toolkit_ids"]) == {a, c}

        after = await _read_grants(cid)
        assert set(after) == {a, c}
        # Survivor's audit fields preserved.
        assert after[a]["granted_at"] == a_original_at
        assert after[a]["granted_by"] is not None
    finally:
        await _cleanup(cid, a, b, c)


@pytest.mark.asyncio
async def test_replace_grants_rolls_back_on_unknown_toolkit(admin_client):
    """A single unknown toolkit_id must roll back the whole call — no partial
    state. With the old POST/DELETE-per-step flow the UI could end up half-
    applied on the same kind of failure.
    """
    cid = "agnt_put_grants_unknown_aaaaaa"
    a = "tk_put_unknown_a"
    await _seed_agent(cid)
    await _seed_toolkit(a)

    try:
        admin_client.post(f"/agents/{cid}/grants", json={"toolkit_id": a})
        before = await _read_grants(cid)
        assert set(before) == {a}

        # Try to replace [a] with [b, doesnt_exist]. Server must reject and
        # leave [a] intact.
        r = admin_client.put(
            f"/agents/{cid}/grants",
            json={"toolkit_ids": [a, "tk_put_unknown_does_not_exist"]},
        )
        assert r.status_code == 404, r.text

        after = await _read_grants(cid)
        assert set(after) == {a}, "rollback failed — partial state visible"
    finally:
        await _cleanup(cid, a)


@pytest.mark.asyncio
async def test_replace_grants_rolls_back_on_disabled_toolkit(admin_client):
    cid = "agnt_put_grants_disabled_aaaaa"
    a = "tk_put_disabled_a"
    bad = "tk_put_disabled_bad"
    await _seed_agent(cid)
    await _seed_toolkit(a)
    await _seed_toolkit(bad, disabled=True)

    try:
        admin_client.post(f"/agents/{cid}/grants", json={"toolkit_id": a})
        before = await _read_grants(cid)
        assert set(before) == {a}

        r = admin_client.put(
            f"/agents/{cid}/grants",
            json={"toolkit_ids": [a, bad]},
        )
        assert r.status_code == 409, r.text

        after = await _read_grants(cid)
        assert set(after) == {a}, "rollback failed on disabled-toolkit reject"
    finally:
        await _cleanup(cid, a, bad)


@pytest.mark.asyncio
async def test_replace_grants_with_empty_set_revokes_all(admin_client):
    cid = "agnt_put_grants_empty_aaaaaaa"
    a, b = "tk_put_empty_a", "tk_put_empty_b"
    await _seed_agent(cid)
    for tid in (a, b):
        await _seed_toolkit(tid)

    try:
        for tid in (a, b):
            admin_client.post(f"/agents/{cid}/grants", json={"toolkit_id": tid})
        assert set(await _read_grants(cid)) == {a, b}

        r = admin_client.put(f"/agents/{cid}/grants", json={"toolkit_ids": []})
        assert r.status_code == 200, r.text
        assert set(r.json()["removed"]) == {a, b}
        assert r.json()["added"] == []

        assert await _read_grants(cid) == {}
    finally:
        await _cleanup(cid, a, b)


@pytest.mark.asyncio
async def test_replace_grants_idempotent_when_nothing_changes(admin_client):
    cid = "agnt_put_grants_noop_aaaaaaaa"
    a = "tk_put_noop_a"
    await _seed_agent(cid)
    await _seed_toolkit(a)

    try:
        admin_client.post(f"/agents/{cid}/grants", json={"toolkit_id": a})
        before = await _read_grants(cid)

        r = admin_client.put(f"/agents/{cid}/grants", json={"toolkit_ids": [a]})
        assert r.status_code == 200
        assert r.json()["added"] == []
        assert r.json()["removed"] == []

        after = await _read_grants(cid)
        assert before == after, "idempotent PUT should not touch granted_at"
    finally:
        await _cleanup(cid, a)


@pytest.mark.asyncio
async def test_replace_grants_404_when_agent_missing(admin_client):
    r = admin_client.put(
        "/agents/agnt_does_not_exist_xxxxxx/grants",
        json={"toolkit_ids": []},
    )
    assert r.status_code == 404
