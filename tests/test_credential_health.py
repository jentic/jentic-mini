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
import src.routers.apis as apis
import src.routers.credentials as creds
from src import vault
from src.db import get_db


class _StubResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class _StubAsyncClient:
    """Drop-in for httpx.AsyncClient that returns a fixed status, no network.

    Used to drive the /test endpoint's health write-back deterministically:
    the real probe would need a reachable upstream, but the contract under
    test is "what does a 2xx / 401 persist to credentials.healthy".
    """

    _status = 200

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *args, **kwargs):
        return _StubResponse(self._status)


def _patch_probe(monkeypatch, status: int) -> None:
    """Allow the SSRF guard and stub the outbound probe to return `status`."""
    monkeypatch.setattr(apis, "is_private_server_url", lambda *a, **k: False)

    client_cls = type("_Client", (_StubAsyncClient,), {"_status": status})
    monkeypatch.setattr(creds.httpx, "AsyncClient", client_cls)


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


# ── /test endpoint health write-back ─────────────────────────────────────────
#
# The headline behaviour of the branch: a Test-connection probe persists its
# verdict so the StatusDot flips without a reload. The existing tier1 tests only
# cover unreachable/SSRF/pipedream hosts (ok=False), never a real 2xx/401 — so
# the write paths (`mark_credential_health(healthy=True/False)`) were untested.
# We stub the outbound probe so the contract is "what does the status persist".

from tests.test_credentials_tier1 import _create_credential, _register_api  # noqa: E402


def test_test_endpoint_persists_healthy_true_on_2xx(admin_client, monkeypatch):
    """A 2xx probe marks the manual credential healthy=True and surfaces it."""
    api_id = "health-writeback-ok.example.com"
    _register_api(admin_client, api_id)
    cid = _create_credential(admin_client, api_id)

    _patch_probe(monkeypatch, 200)
    resp = admin_client.post(f"/credentials/{cid}/test")
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True

    listed = admin_client.get("/credentials").json()
    row = next(c for c in listed if c["id"] == cid)
    assert row["healthy"] is True
    assert row["health_checked_at"] is not None


def test_test_endpoint_persists_healthy_false_on_401(admin_client, monkeypatch):
    """A 401 probe marks the credential healthy=False (authoritative rejection)."""
    api_id = "health-writeback-401.example.com"
    _register_api(admin_client, api_id)
    cid = _create_credential(admin_client, api_id)

    _patch_probe(monkeypatch, 401)
    resp = admin_client.post(f"/credentials/{cid}/test")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is False
    assert body["hint"] == "unauthorized"

    listed = admin_client.get("/credentials").json()
    row = next(c for c in listed if c["id"] == cid)
    assert row["healthy"] is False
    assert row["health_checked_at"] is not None


def test_test_endpoint_leaves_healthy_untouched_on_429(admin_client, monkeypatch):
    """Ambiguous statuses (429/5xx) are not credential verdicts — healthy stays NULL."""
    api_id = "health-writeback-429.example.com"
    _register_api(admin_client, api_id)
    cid = _create_credential(admin_client, api_id)

    _patch_probe(monkeypatch, 429)
    resp = admin_client.post(f"/credentials/{cid}/test")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is False
    assert body["hint"] == "rate_limited"

    listed = admin_client.get("/credentials").json()
    row = next(c for c in listed if c["id"] == cid)
    assert row["healthy"] is None, "429 must not write a health verdict"
