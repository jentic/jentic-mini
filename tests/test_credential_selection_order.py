"""Determinism of get_credential_ids_for_route ordering on equal path_prefix length."""

import asyncio
import os
import uuid

import aiosqlite
import pytest
import src.vault as vault


HOST = "192.0.2.10"  # TEST-NET, guaranteed non-routable
CRED_Z = "z-cred-for-order-test"
CRED_A = "a-cred-for-order-test"


@pytest.fixture(scope="module")
def two_equal_prefix_creds(client):
    """Insert two credentials for the same host with the same (default) path_prefix."""

    async def setup():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO apis (id, name, base_url) VALUES (?, ?, ?)",
                (HOST, "Order Test API", f"https://{HOST}"),
            )
            for cred_id in (CRED_Z, CRED_A):
                enc = vault.encrypt(f"token-{cred_id}")
                await db.execute(
                    "INSERT OR IGNORE INTO credentials "
                    "(id, label, env_var, encrypted_value, api_id, auth_type) "
                    "VALUES (?, ?, ?, ?, ?, 'bearer')",
                    (cred_id, cred_id, cred_id.upper(), enc, HOST),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO credential_routes (credential_id, host) VALUES (?, ?)",
                    (cred_id, HOST),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO toolkit_credentials (id, toolkit_id, credential_id) "
                    "VALUES (?, 'default', ?)",
                    (str(uuid.uuid4()), cred_id),
                )
            await db.commit()

    asyncio.run(setup())
    yield

    async def teardown():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            for cred_id in (CRED_Z, CRED_A):
                await db.execute("DELETE FROM credential_routes WHERE credential_id=?", (cred_id,))
                await db.execute(
                    "DELETE FROM toolkit_credentials WHERE credential_id=?", (cred_id,)
                )
                await db.execute("DELETE FROM credentials WHERE id=?", (cred_id,))
            await db.execute("DELETE FROM apis WHERE id=?", (HOST,))
            await db.commit()

    asyncio.run(teardown())


def test_credential_order_is_deterministic(two_equal_prefix_creds):
    """Same-prefix credentials must be returned in alphabetical ID order, not DB row order."""

    async def get_ids():
        return await vault.get_credential_ids_for_route("default", HOST, "/")

    ids = asyncio.run(get_ids())
    assert len(ids) == 2, f"Expected 2 credentials, got {ids}"
    assert ids == sorted(ids), f"Credentials not in deterministic (alphabetical) order: {ids}"
    assert ids[0] == CRED_A, f"Expected '{CRED_A}' first (alphabetically), got '{ids[0]}'"
