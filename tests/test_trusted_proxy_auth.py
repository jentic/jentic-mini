"""
Trusted-proxy forwarded identity authentication tests — Phase 28.

Covers all eight validation criteria from
specs/2026-05-12-trusted-proxy-forwarded-identity/validation.md:

1. Default (no env) — proxy path inactive, normal 401/logged_in:false behaviour.
2. Trusted peer + header → 200, correct identity, JIT row created.
3. Trusted peer + header absent → 401.
4. Untrusted peer + header → 401 + WARN on jentic.auth.
5. Trusted peer + spoofed X-Forwarded-For → still authenticated (peer IP is gate).
6. JIT account at /user/login → 401 invalid_credentials; /user/token → 401
   invalid_client; no 500 on either.
7. Trusted peer + X-Forwarded-Prefix: /foo → root_path applied.
8. Untrusted peer + X-Forwarded-Prefix: /foo → root_path unset + WARN on jentic.auth.
"""

import logging
import sqlite3
from pathlib import Path

import pytest
from src.db import DB_PATH
from starlette.testclient import TestClient


TRUSTED_IP = "10.0.0.1"  # inside 10.0.0.0/8
UNTRUSTED_IP = "203.0.113.5"  # TEST-NET-3, never RFC-1918
PROXY_CIDR = "10.0.0.0/8"
PROXY_HEADER = "X-Remote-User"
PROXY_IDENTITY = "proxy-user@example.com"


@pytest.fixture
def proxy_env(monkeypatch):
    """Activate trusted-proxy auth by patching module-level config vars."""
    monkeypatch.setattr("src.auth.JENTIC_TRUSTED_PROXY_HEADER", PROXY_HEADER)
    monkeypatch.setattr("src.auth.JENTIC_TRUSTED_PROXY_NETS", PROXY_CIDR)
    monkeypatch.setattr("src.main.JENTIC_TRUSTED_PROXY_HEADER", PROXY_HEADER)
    monkeypatch.setattr("src.main.JENTIC_TRUSTED_PROXY_NETS", PROXY_CIDR)


@pytest.fixture
def trusted_client(app, proxy_env):
    """TestClient with a peer IP inside PROXY_CIDR and proxy env active."""
    with TestClient(app, raise_server_exceptions=False, client=(TRUSTED_IP, 50010)) as c:
        yield c


@pytest.fixture
def untrusted_client(app, proxy_env):
    """TestClient with a peer IP outside PROXY_CIDR and proxy env active."""
    with TestClient(app, raise_server_exceptions=False, client=(UNTRUSTED_IP, 50011)) as c:
        yield c


def _jit_row(username: str) -> dict | None:
    """Synchronous DB lookup for a users row by username."""
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cur = db.execute(
            "SELECT password_hash, created_via FROM users WHERE username = ?",
            (username,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


# ── 1. Default (no env) ──────────────────────────────────────────────────────


def test_no_env_protected_endpoint_is_401(client):
    resp = client.get("/toolkits")
    assert resp.status_code == 401


def test_no_env_user_me_not_logged_in(client):
    resp = client.get("/user/me")
    assert resp.status_code == 200
    assert resp.json()["logged_in"] is False


# ── 2. Trusted peer + header → 200 + identity + JIT row ─────────────────────


def test_trusted_peer_with_header_is_authenticated(trusted_client):
    resp = trusted_client.get("/user/me", headers={PROXY_HEADER: PROXY_IDENTITY})
    assert resp.status_code == 200
    body = resp.json()
    assert body["logged_in"] is True
    assert body["username"] == PROXY_IDENTITY


def test_trusted_peer_jit_row_created(trusted_client):
    trusted_client.get("/user/me", headers={PROXY_HEADER: PROXY_IDENTITY})
    row = _jit_row(PROXY_IDENTITY)
    assert row is not None
    assert row["password_hash"] is None
    assert row["created_via"] == "trusted_proxy"


# ── 3. Trusted peer + no header → 401 ───────────────────────────────────────


def test_trusted_peer_no_header_is_401(trusted_client):
    resp = trusted_client.get("/toolkits")
    assert resp.status_code == 401


# ── 4. Untrusted peer + header → 401 + WARN ─────────────────────────────────


def test_untrusted_peer_with_header_is_401(untrusted_client, caplog):
    caplog.set_level(logging.WARNING)
    resp = untrusted_client.get("/toolkits", headers={PROXY_HEADER: PROXY_IDENTITY})
    assert resp.status_code == 401
    warn_msgs = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any(UNTRUSTED_IP in m for m in warn_msgs), f"No WARN with peer IP: {warn_msgs}"
    assert any(PROXY_HEADER in m for m in warn_msgs), f"No WARN with header name: {warn_msgs}"


# ── 5. Spoofed X-Forwarded-For doesn't affect auth ──────────────────────────


def test_trusted_peer_spoofed_xff_still_authenticated(trusted_client):
    """Peer IP from ASGI scope beats XFF — spoofing XFF cannot downgrade a trusted peer."""
    resp = trusted_client.get(
        "/user/me",
        headers={PROXY_HEADER: PROXY_IDENTITY, "X-Forwarded-For": UNTRUSTED_IP},
    )
    assert resp.status_code == 200
    assert resp.json()["logged_in"] is True


# ── 6. JIT account cannot use /user/login or /user/token ────────────────────


def test_jit_account_login_returns_401_not_500(trusted_client, client):
    trusted_client.get("/user/me", headers={PROXY_HEADER: PROXY_IDENTITY})
    resp = client.post("/user/login", json={"username": PROXY_IDENTITY, "password": "anything"})
    assert resp.status_code == 401
    detail = resp.json().get("detail", {})
    assert detail.get("error") == "invalid_credentials"


def test_jit_account_token_returns_401_not_500(trusted_client, client):
    trusted_client.get("/user/me", headers={PROXY_HEADER: PROXY_IDENTITY})
    resp = client.post(
        "/user/token",
        data={"username": PROXY_IDENTITY, "password": "anything", "grant_type": "password"},
    )
    assert resp.status_code == 401
    detail = resp.json().get("detail", {})
    assert detail.get("error") == "invalid_client"


# ── 7. Trusted peer + X-Forwarded-Prefix → root_path applied ────────────────


def test_trusted_peer_forwarded_prefix_applied(trusted_client, monkeypatch):
    fixtures_dir = Path(__file__).parent / "fixtures"
    monkeypatch.setattr("src.main.STATIC_DIR", fixtures_dir)
    resp = trusted_client.get("/", headers={"Accept": "text/html", "X-Forwarded-Prefix": "/foo"})
    assert resp.status_code == 200
    assert b'href="/foo/"' in resp.content


# ── 8. Untrusted peer + X-Forwarded-Prefix → root_path unset + WARN ─────────


def test_untrusted_peer_forwarded_prefix_ignored(untrusted_client, monkeypatch, caplog):
    fixtures_dir = Path(__file__).parent / "fixtures"
    monkeypatch.setattr("src.main.STATIC_DIR", fixtures_dir)
    caplog.set_level(logging.WARNING)
    resp = untrusted_client.get("/", headers={"Accept": "text/html", "X-Forwarded-Prefix": "/foo"})
    assert resp.status_code == 200
    assert b'href="/foo/"' not in resp.content
    warn_msgs = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("FORWARDED_PREFIX" in m for m in warn_msgs), f"No WARN: {warn_msgs}"


# ── Additional: half-config inactive + tk_ key takes precedence ─────────────


def test_only_header_env_set_path_inactive(app, monkeypatch):
    """Only JENTIC_TRUSTED_PROXY_HEADER set — proxy path stays inactive."""
    monkeypatch.setattr("src.auth.JENTIC_TRUSTED_PROXY_HEADER", PROXY_HEADER)
    monkeypatch.setattr("src.auth.JENTIC_TRUSTED_PROXY_NETS", "")
    with TestClient(app, raise_server_exceptions=False, client=(TRUSTED_IP, 50014)) as c:
        resp = c.get("/toolkits", headers={PROXY_HEADER: PROXY_IDENTITY})
    assert resp.status_code == 401


def test_only_nets_env_set_path_inactive(app, monkeypatch):
    """Only JENTIC_TRUSTED_PROXY_NETS set — proxy path stays inactive."""
    monkeypatch.setattr("src.auth.JENTIC_TRUSTED_PROXY_HEADER", "")
    monkeypatch.setattr("src.auth.JENTIC_TRUSTED_PROXY_NETS", PROXY_CIDR)
    with TestClient(app, raise_server_exceptions=False, client=(TRUSTED_IP, 50015)) as c:
        resp = c.get("/toolkits", headers={PROXY_HEADER: PROXY_IDENTITY})
    assert resp.status_code == 401


def test_tk_key_takes_precedence_over_proxy_header(app, proxy_env, agent_key):
    """tk_ key must remain authoritative even when the proxy header is also present."""
    with TestClient(app, raise_server_exceptions=False, client=(TRUSTED_IP, 50016)) as c:
        resp = c.get(
            "/user/me",
            headers={
                PROXY_HEADER: PROXY_IDENTITY,
                "X-Jentic-API-Key": agent_key,
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    # A tk_ key produces agent_key=True, not a human session with is_admin.
    assert body.get("logged_in") is False
    assert body.get("agent_key") is True
