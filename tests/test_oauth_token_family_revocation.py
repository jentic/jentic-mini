"""Refresh-token reuse triggers full family revocation (RFC 6749 BCP §4.14)."""

import aiosqlite
import pytest
from src.db import DB_PATH
from src.routers.oauth_agent import _revoke_token_family  # noqa: PLC2701


@pytest.mark.asyncio
async def test_revoke_token_family_walks_chain_and_deletes_all(client):
    """Seed a refresh chain R0 → R1 → R2 (each access-paired) and confirm that
    presenting any consumed link via _revoke_token_family wipes the entire family.
    """
    cid = "agnt_family_test"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO agents (client_id, client_name, jwks_json, status, created_at)
               VALUES (?, ?, '{}', 'approved', strftime('%s','now'))""",
            (cid, "family-test"),
        )
        await db.executemany(
            """INSERT INTO agent_tokens
                  (token_hash, client_id, token_type, expires_at, parent_token_hash, consumed_at)
               VALUES (?, ?, ?, 9999999999, ?, ?)""",
            [
                ("rt0_h", cid, "refresh", None, 100.0),
                ("at0_h", cid, "access", "rt0_h", None),
                ("rt1_h", cid, "refresh", "rt0_h", 200.0),
                ("at1_h", cid, "access", "rt1_h", None),
                ("rt2_h", cid, "refresh", "rt1_h", None),
                ("at2_h", cid, "access", "rt2_h", None),
            ],
        )
        await db.commit()

    await _revoke_token_family("rt1_h")

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT count(*) FROM agent_tokens WHERE client_id=?", (cid,)) as cur:
            (remaining,) = await cur.fetchone()
        await db.execute("DELETE FROM agents WHERE client_id=?", (cid,))
        await db.commit()

    assert remaining == 0, f"expected entire family wiped, {remaining} tokens left"


@pytest.mark.asyncio
async def test_revoke_token_family_leaves_other_chains_alone(client):
    """A separate, unrelated chain must survive a sibling family being wiped."""
    cid = "agnt_isolation_test"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO agents (client_id, client_name, jwks_json, status, created_at)
               VALUES (?, ?, '{}', 'approved', strftime('%s','now'))""",
            (cid, "isolation-test"),
        )
        await db.executemany(
            """INSERT INTO agent_tokens
                  (token_hash, client_id, token_type, expires_at, parent_token_hash, consumed_at)
               VALUES (?, ?, ?, 9999999999, ?, ?)""",
            [
                ("a_root", cid, "refresh", None, 100.0),
                ("a_child", cid, "refresh", "a_root", None),
                ("b_root", cid, "refresh", None, None),
                ("b_child", cid, "access", "b_root", None),
            ],
        )
        await db.commit()

    await _revoke_token_family("a_child")

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT token_hash FROM agent_tokens WHERE client_id=? ORDER BY token_hash",
            (cid,),
        ) as cur:
            survivors = [r[0] for r in await cur.fetchall()]
        await db.execute("DELETE FROM agents WHERE client_id=?", (cid,))
        await db.commit()

    assert survivors == ["b_child", "b_root"]
