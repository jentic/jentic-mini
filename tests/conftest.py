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

import pytest
from contextlib import asynccontextmanager
from starlette.testclient import TestClient

from src.db import run_migrations


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


@pytest.fixture(scope="session")
def client(app):
    """Session-scoped test client. All tests share the same DB."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="session")
def admin_session(client):
    """Create an admin account and return session cookies for use with `cookies=` in requests."""
    # Create account (first-time setup)
    resp = client.post("/user/create", json={
        "username": "testadmin",
        "password": "testpassword123",
    })
    assert resp.status_code in (200, 201, 410), f"Failed to create user: {resp.text}"

    # Login
    resp = client.post("/user/login", json={
        "username": "testadmin",
        "password": "testpassword123",
    })
    assert resp.status_code == 200, f"Failed to login: {resp.text}"

    # Extract session cookie
    cookies = dict(resp.cookies)
    return cookies


@pytest.fixture(scope="session")
def agent_key(client, admin_session):
    """Get an agent API key — either from first-time generation or by creating a toolkit key."""
    # Try the first-time generation path (trusted subnet check requires forwarded IP)
    resp = client.post("/default-api-key/generate", headers={"X-Forwarded-For": "127.0.0.1"})
    if resp.status_code in (200, 201):
        return resp.json()["key"]
    default_key_status, default_key_body = resp.status_code, resp.text
    # Already claimed — create a new key on the default toolkit
    resp = client.post("/toolkits/default/keys", cookies=admin_session, json={"label": "test-agent"})
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
def agent_only_client(app, agent_key, client):
    """A TestClient with no session cookies — only agent key auth.

    Separate from the main `client` fixture to avoid session cookie
    leaking into agent auth tests (the shared client accumulates
    cookies from admin_session). Depends on `client` to ensure the
    app lifespan has already started.
    """
    with TestClient(app, raise_server_exceptions=False) as c:
        c.headers["X-Jentic-API-Key"] = agent_key
        yield c


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    """Remove temp directory after all tests complete."""
    import shutil
    yield
    shutil.rmtree(_test_dir, ignore_errors=True)
