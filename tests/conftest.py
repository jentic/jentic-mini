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
_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db.close()
os.environ["DB_PATH"] = _test_db.name
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
    _app.router.lifespan_context = _test_lifespan
    return _app


@pytest.fixture(scope="session")
def client(app):
    """Session-scoped test client. All tests share the same DB."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="session")
def admin_session(client):
    """Create an admin account and return a client-like callable with the session cookie."""
    # Create account (first-time setup)
    resp = client.post("/user/create", json={
        "username": "testadmin",
        "password": "testpassword123",
    })
    assert resp.status_code in (200, 201, 409), f"Failed to create user: {resp.text}"

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
    # Try the first-time generation path
    resp = client.post("/default-api-key/generate")
    if resp.status_code == 200:
        return resp.json()["key"]
    # Already claimed — create a new key on the default toolkit
    resp = client.post("/toolkits/default/keys", cookies=admin_session, json={"name": "test-agent"})
    if resp.status_code in (200, 201):
        return resp.json()["key"]
    return None


@pytest.fixture(scope="session")
def agent_key_header(agent_key):
    """Return the auth header dict for agent requests."""
    if agent_key is None:
        pytest.skip("No agent key available")
    return {"X-Jentic-API-Key": agent_key}


def _authed_get(client, url, cookies):
    """Helper: GET with admin session cookies."""
    return client.get(url, cookies=cookies)


def _authed_post(client, url, cookies, **kwargs):
    """Helper: POST with admin session cookies."""
    return client.post(url, cookies=cookies, **kwargs)


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    """Remove temp DB after all tests complete."""
    yield
    try:
        os.unlink(_test_db.name)
    except OSError:
        pass
