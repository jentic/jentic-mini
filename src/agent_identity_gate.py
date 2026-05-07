"""Shared async checks for agent identity (middleware + OAuth routes)."""

import time

import aiosqlite

from src.agent_identity_util import hash_token
from src.db import DB_PATH


async def verify_registration_access_token(client_id: str, raw_rat: str) -> bool:
    """True if raw_rat is the current non-expired registration_access_token for client_id."""
    if not raw_rat.startswith("rat_"):
        return False
    h = hash_token(raw_rat)
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT registration_token_hash, registration_token_expires_at
               FROM agents WHERE client_id=? AND deleted_at IS NULL""",
            (client_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return False
    if row["registration_token_hash"] != h:
        return False
    if (row["registration_token_expires_at"] or 0) < now:
        return False
    return True
