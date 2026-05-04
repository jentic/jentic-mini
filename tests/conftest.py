"""
Test harness infrastructure for Jentic Mini backend.

Sets up a temp SQLite database, runs Alembic migrations, and provides
a FastAPI TestClient with auth helper fixtures. All tests hit the real
HTTP API — no mocking of the database or vault.
"""

import os
import tempfile


# ── DB_PATH must be set BEFORE any src.* imports ──────────────────────────────
# src/config.py reads DB_PATH at import time, so we override it here.
# Using a dedicated temp directory isolates DB + any artifacts and ensures
# clean teardown with no cross-run interference.
_test_dir = tempfile.mkdtemp(prefix="jentic-test-")
os.environ["DB_PATH"] = os.path.join(_test_dir, "test.db")
os.environ["JENTIC_TELEMETRY"] = "off"
os.environ["APP_VERSION"] = "0.0.0-test"

from contextlib import asynccontextmanager

import pytest
from src.db import run_migrations
from starlette.testclient import TestClient


@asynccontextmanager
async def _test_lifespan(app):
    """Minimal lifespan for tests — only runs DB migrations.

    Skips BM25 index rebuild, self-registration, catalog refresh,
    and OAuth broker loading (all require network or side effects).
    """
    run_migrations()
    yield


@pytest.fixture(scope="session")
def app():
    """Create a FastAPI app with test lifespan."""
    from src.main import app as _app

    # NB: mutates the singleton app — safe for tests but not reversible
    _app.router.lifespan_context = _test_lifespan
    return _app


# Client address used for all TestClients. 127.0.0.1 is in the default trusted
# subnets (`src.auth._DEFAULT_TRUSTED_SUBNETS`), so agent keys — which are
# issued with `allowed_ips = default_allowed_ips()` — pass the IP check without
# needing an X-Forwarded-For shim or an admin JWT fallback.
_TEST_CLIENT_ADDR = ("127.0.0.1", 50000)


@pytest.fixture(scope="session")
def client(app):
    """Session-scoped unauthenticated TestClient. All tests share the same DB."""
    with TestClient(app, raise_server_exceptions=False, client=_TEST_CLIENT_ADDR) as c:
        yield c


@pytest.fixture(scope="session")
def admin_client(app, client):
    """Isolated TestClient with an authenticated admin session.

    A separate TestClient instance — cookies set on the instance rather than
    per-request (which starlette has deprecated). Keeping this isolated from
    the shared `client` means tests that expect 401 from an unauthenticated
    client stay deterministic regardless of fixture ordering.

    Depends on `client` to ensure the app lifespan (and migrations) have run.
    """
    with TestClient(app, raise_server_exceptions=False, client=_TEST_CLIENT_ADDR) as c:
        # Create account (first-time setup)
        resp = c.post(
            "/user/create",
            json={
                "username": "testadmin",
                "password": "testpassword123",
            },
        )
        assert resp.status_code in (200, 201, 410), f"Failed to create user: {resp.text}"

        # Login — TestClient persists Set-Cookie on the instance automatically
        resp = c.post(
            "/user/login",
            json={
                "username": "testadmin",
                "password": "testpassword123",
            },
        )
        assert resp.status_code == 200, f"Failed to login: {resp.text}"

        yield c


@pytest.fixture(scope="session")
def agent_key(client, admin_client):
    """Get an agent API key — either from first-time generation or by creating a toolkit key."""
    # Try the first-time generation path (client IP 127.0.0.1 is trusted)
    resp = client.post("/default-api-key/generate")
    if resp.status_code in (200, 201):
        return resp.json()["key"]
    default_key_status, default_key_body = resp.status_code, resp.text
    # Already claimed — create a new key on the default toolkit
    resp = admin_client.post("/toolkits/default/keys", json={"label": "test-agent"})
    if resp.status_code in (200, 201):
        return resp.json()["key"]
    pytest.fail(
        f"/default-api-key/generate returned {default_key_status} ({default_key_body}); "
        f"/toolkits/default/keys returned {resp.status_code} ({resp.text})"
    )


@pytest.fixture(scope="session")
def agent_key_header(agent_key):
    """Return the auth header dict for agent requests."""
    return {"X-Jentic-API-Key": agent_key}


@pytest.fixture(scope="session")
def agent_only_client(app, agent_key):
    """A TestClient with only agent-key auth — no admin session cookies."""
    with TestClient(app, raise_server_exceptions=False, client=_TEST_CLIENT_ADDR) as c:
        c.headers["X-Jentic-API-Key"] = agent_key
        yield c


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    """Remove temp directory after all tests complete."""
    import shutil

    yield
    shutil.rmtree(_test_dir, ignore_errors=True)
