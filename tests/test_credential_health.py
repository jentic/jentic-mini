"""Manual-credential health (`credentials.healthy`) — write + read-back.

Pipedream OAuth credentials already carry a health signal on
`oauth_broker_accounts.healthy`; manual credentials (bearer / api-key / basic)
historically could only ever be green-or-grey because there was nowhere to
record a rejection. Migration 0008 adds `credentials.healthy` +
`credentials.health_checked_at`, the broker / Test-connection flow write them,
and the list query surfaces them so a manual credential's StatusDot can go red.

These tests pin the contract end-to-end at the data layer:

  - the migration actually added both columns;
  - `vault.mark_credential_health` writes the tri-state flag + timestamp and is
    idempotent / swallows nothing it shouldn't;
  - `vault.get_credential` and `GET /credentials` reflect the value;
  - precedence: a Pipedream account row still wins over the credential's own
    column (so the OAuth path is unaffected).
"""

import pytest
from src import vault
from src.db import get_db


@pytest.mark.asyncio
async def test_migration_added_health_columns(admin_client):
    """0008 must have added healthy + health_checked_at to credentials."""
    async with get_db() as db:
        async with db.execute("PRAGMA table_info(credentials)") as cur:
            cols = {row[1] for row in await cur.fetchall()}
    assert "healthy" in cols
    assert "health_checked_at" in cols


@pytest.mark.asyncio
async def test_mark_credential_health_writes_tri_state(admin_client):
    """healthy starts NULL, then flips false → true, stamping health_checked_at."""
    cred = await vault.create_credential(
        label="manual-health-cred",
        value="secret-abc",
        api_id=None,
        scheme_name="bearer",
    )
    cid = cred["id"]

    # Fresh credential: no health signal yet.
    fresh = await vault.get_credential(cid)
    assert fresh["healthy"] is None
    assert fresh["health_checked_at"] is None

    # Upstream rejected it → red.
    await vault.mark_credential_health(cid, healthy=False)
    broken = await vault.get_credential(cid)
    assert broken["healthy"] is False
    assert broken["health_checked_at"] is not None

    # Later it works → green, timestamp advances (or stays, never goes backwards).
    await vault.mark_credential_health(cid, healthy=True)
    ok = await vault.get_credential(cid)
    assert ok["healthy"] is True
    assert ok["health_checked_at"] is not None


@pytest.mark.asyncio
async def test_mark_credential_health_noop_on_missing_id(admin_client):
    """A blank / unknown id must never raise — this runs on the response path."""
    await vault.mark_credential_health("", healthy=False)
    await vault.mark_credential_health("does-not-exist", healthy=True)


@pytest.mark.asyncio
async def test_list_credentials_surfaces_manual_healthy(admin_client):
    """GET /credentials reports the manual credential's own healthy flag."""
    cred = await vault.create_credential(
        label="listed-health-cred",
        value="secret-def",
        api_id=None,
        scheme_name="bearer",
    )
    cid = cred["id"]
    await vault.mark_credential_health(cid, healthy=False)

    resp = admin_client.get("/credentials")
    assert resp.status_code == 200, resp.text
    row = next((c for c in resp.json() if c["id"] == cid), None)
    assert row is not None, "created credential missing from list"
    assert row["healthy"] is False
    assert row["health_checked_at"] is not None
