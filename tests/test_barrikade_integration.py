import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest
from src import vault
from src.security import security_registry
from src.security.barrikade import BarrikadePlugin
from src.security.plugin import SecurityPlugin, SecurityVerdict


EGRESS_HOST = "barrikade-egress.com"


@pytest.fixture(scope="module")
def barrikade_test_credentials():
    """Set up a mock credential and policy for egress host testing."""

    async def setup():
        db_path = os.environ["DB_PATH"]
        enc = vault.encrypt("mock-secret")
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO credentials "
                "(id, label, env_var, encrypted_value, api_id, auth_type, identity, scheme) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "barrikade-egress-cred",
                    "Egress Test Credential",
                    "BARRIKADE_EGRESS_CRED",
                    enc,
                    EGRESS_HOST,
                    "bearer",
                    None,
                    json.dumps({"in": "header", "name": "Authorization", "prefix": "Bearer "}),
                ),
            )
            await db.execute(
                "INSERT OR IGNORE INTO credential_routes (credential_id, host) VALUES (?, ?)",
                ("barrikade-egress-cred", EGRESS_HOST),
            )
            await db.execute(
                "INSERT OR IGNORE INTO toolkit_credentials (toolkit_id, credential_id) VALUES ('default', ?)",
                ("barrikade-egress-cred",),
            )
            # Add explicit allow rule to override Jentic's default deny posture on write methods
            now = time.time()
            await db.execute(
                "INSERT OR IGNORE INTO credential_policies (id, credential_id, rules, summary, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "barrikade-egress-policy",
                    "barrikade-egress-cred",
                    json.dumps([{"effect": "allow", "path": ".*"}]),
                    "Allow all for barrikade egress testing",
                    now,
                    now,
                ),
            )
            await db.commit()

    asyncio.run(setup())
    yield

    async def teardown():
        db_path = os.environ["DB_PATH"]
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "DELETE FROM credential_policies WHERE credential_id=?", ("barrikade-egress-cred",)
            )
            await db.execute(
                "DELETE FROM credential_routes WHERE credential_id=?", ("barrikade-egress-cred",)
            )
            await db.execute(
                "DELETE FROM toolkit_credentials WHERE credential_id=?", ("barrikade-egress-cred",)
            )
            await db.execute("DELETE FROM credentials WHERE id=?", ("barrikade-egress-cred",))
            await db.commit()

    asyncio.run(teardown())


# Mock plugin helper


class _MockSecurityPlugin(SecurityPlugin):
    """A lightweight mock plugin for testing the registry-based flow."""

    name = "mock-security"

    def __init__(self, scan_result: SecurityVerdict):
        self._scan_result = scan_result
        self.calls: list[str] = []

    async def scan_text(self, text: str) -> SecurityVerdict:
        self.calls.append(text)
        return self._scan_result


@pytest.fixture()
def _register_mock_plugin():
    """Context-manager fixture that registers a mock plugin on the registry.

    Yields a factory: call it with a ``SecurityVerdict`` to get the
    ``_MockSecurityPlugin`` instance.  The plugin is deregistered on teardown.
    """
    plugins: list[_MockSecurityPlugin] = []

    def _factory(verdict: SecurityVerdict) -> _MockSecurityPlugin:
        p = _MockSecurityPlugin(verdict)
        security_registry.register(p)
        plugins.append(p)
        return p

    yield _factory

    for p in plugins:
        security_registry.deregister(p.name)


# BarrikadePlugin unit tests


@pytest.mark.asyncio
async def test_client_scan_text_success():
    """Test BarrikadePlugin returns correctly when mock API succeeds."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "final_verdict": "pass",
        "decision_layer": "test",
        "confidence_score": 0.99,
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_client):
        plugin = BarrikadePlugin(url="http://mock-barrikade", timeout_ms=5000, fail_open=True)
        res = await plugin.scan_text("safe input")
        assert res.is_safe is True
        assert res.verdict == "pass"
        assert res.confidence_score == 0.99


@pytest.mark.asyncio
async def test_client_scan_text_blocked():
    """Test BarrikadePlugin returns is_safe=False when verdict is block."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "final_verdict": "block",
        "decision_layer": "test",
        "confidence_score": 0.95,
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_client):
        plugin = BarrikadePlugin(url="http://mock-barrikade", timeout_ms=5000, fail_open=True)
        res = await plugin.scan_text("unsafe input")
        assert res.is_safe is False
        assert res.verdict == "block"
        assert res.confidence_score == 0.95


@pytest.mark.asyncio
async def test_client_fail_open_on_exception():
    """Test BarrikadePlugin fail-open and fail-closed behaviors under exception."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post.side_effect = Exception("Connection refused")

    with patch("httpx.AsyncClient", return_value=mock_client):
        # With fail open = True
        plugin_open = BarrikadePlugin(url="http://mock-barrikade", timeout_ms=5000, fail_open=True)
        res = await plugin_open.scan_text("any input")
        assert res.is_safe is True

        # With fail open = False
        plugin_closed = BarrikadePlugin(
            url="http://mock-barrikade", timeout_ms=5000, fail_open=False
        )
        res = await plugin_closed.scan_text("any input")
        assert res.is_safe is False


# Ingress Middleware Tests


def test_ingress_middleware_safe(client, agent_key_header, _register_mock_plugin):
    """Test safe ingress requests are allowed to proceed."""
    # With no plugins registered — should pass through
    resp = client.get("/search?q=safe", headers=agent_key_header)
    assert resp.status_code == 200

    # With a mock plugin returning safe verdict
    mock_plugin = _register_mock_plugin(
        SecurityVerdict(
            is_safe=True,
            verdict="pass",
            decision_layer="none",
            confidence_score=0.0,
            plugin_name="mock-security",
        )
    )
    resp = client.get("/search?q=safe", headers=agent_key_header)
    assert resp.status_code == 200
    assert "safe" in mock_plugin.calls


def test_ingress_middleware_blocked_search(client, agent_key_header, _register_mock_plugin):
    """Test unsafe search queries are blocked with a 403 security violation."""
    _register_mock_plugin(
        SecurityVerdict(
            is_safe=False,
            verdict="block",
            decision_layer="llm",
            confidence_score=0.98,
            plugin_name="mock-security",
        )
    )
    resp = client.get("/search?q=unsafe-query", headers=agent_key_header)
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"] == "security_violation"
    assert data["verdict"] == "block"
    assert data["decision_layer"] == "llm"
    assert data["confidence_score"] == 0.98


def test_ingress_middleware_blocked_workflow_body(client, agent_key_header, _register_mock_plugin):
    """Test unsafe workflow POST payloads are blocked with a 403."""
    mock_plugin = _register_mock_plugin(
        SecurityVerdict(
            is_safe=False,
            verdict="block",
            decision_layer="heuristic",
            confidence_score=0.85,
            plugin_name="mock-security",
        )
    )
    resp = client.post(
        "/workflows/some-slug",
        json={"user_input": "malicious input here"},
        headers=agent_key_header,
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"] == "security_violation"
    assert "malicious input here" in mock_plugin.calls[0]


# Egress Response Body Tests


def test_egress_response_safe(
    client, agent_key_header, barrikade_test_credentials, _register_mock_plugin
):
    """Test that a safe response body from the upstream API is allowed to pass through."""
    mock_plugin = _register_mock_plugin(
        SecurityVerdict(
            is_safe=True,
            verdict="pass",
            decision_layer="none",
            confidence_score=0.0,
            plugin_name="mock-security",
        )
    )

    # Mock the outbound aiohttp request
    mock_response = AsyncMock()
    mock_response.read.return_value = b'{"status": "succeeded", "message": "all clear"}'
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "application/json"}

    mock_session = AsyncMock()
    client_instance = AsyncMock()
    mock_session.__aenter__.return_value = client_instance

    client_instance.request = MagicMock()
    client_instance.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    client_instance.request.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        resp = client.post(
            f"/{EGRESS_HOST}/v1/charges",
            json={"amount": 100},
            headers=agent_key_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "succeeded"
        assert any("all clear" in c for c in mock_plugin.calls)


def test_egress_response_blocked(
    client, agent_key_header, barrikade_test_credentials, _register_mock_plugin
):
    """Test that an unsafe response body from the upstream API is blocked."""
    mock_plugin = _register_mock_plugin(
        SecurityVerdict(
            is_safe=False,
            verdict="block",
            decision_layer="heuristic",
            confidence_score=0.97,
            plugin_name="mock-security",
        )
    )

    # Mock the outbound aiohttp request to return a suspicious body
    mock_response = AsyncMock()
    mock_response.read.return_value = b'{"exfiltrated_key": "sk_live_12345"}'
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "application/json"}

    mock_session = AsyncMock()
    client_instance = AsyncMock()
    mock_session.__aenter__.return_value = client_instance

    client_instance.request = MagicMock()
    client_instance.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    client_instance.request.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        resp = client.post(
            f"/{EGRESS_HOST}/v1/charges",
            json={"amount": 100},
            headers=agent_key_header,
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["error"] == "security_violation"
        assert "response body from the upstream service was blocked" in data["message"]
        assert data["verdict"] == "block"
        assert any("sk_live_12345" in c for c in mock_plugin.calls)
