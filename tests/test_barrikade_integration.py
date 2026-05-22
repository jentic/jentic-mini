import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest
from src import vault
from src.barrikade_client import BarrikadeClient


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


@pytest.mark.asyncio
async def test_client_scan_text_success():
    """Test client returns correctly when mock API succeeds."""
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
        # Need to patch BARRIKADE_URL to enable the client
        with patch("src.barrikade_client.BARRIKADE_URL", "http://mock-barrikade"):
            res = await BarrikadeClient.scan_text("safe input")
            assert res["is_safe"] is True
            assert res["final_verdict"] == "pass"
            assert res["confidence_score"] == 0.99


@pytest.mark.asyncio
async def test_client_scan_text_blocked():
    """Test client returns is_safe=False when verdict is block."""
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
        with patch("src.barrikade_client.BARRIKADE_URL", "http://mock-barrikade"):
            res = await BarrikadeClient.scan_text("unsafe input")
            assert res["is_safe"] is False
            assert res["final_verdict"] == "block"
            assert res["confidence_score"] == 0.95


@pytest.mark.asyncio
async def test_client_fail_open_on_exception():
    """Test client fail-open and fail-closed behaviors under exception."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post.side_effect = Exception("Connection refused")

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch("src.barrikade_client.BARRIKADE_URL", "http://mock-barrikade"):
            # With fail open = True (default)
            with patch("src.barrikade_client.BARRIKADE_FAIL_OPEN", True):
                res = await BarrikadeClient.scan_text("any input")
                assert res["is_safe"] is True

            # With fail open = False
            with patch("src.barrikade_client.BARRIKADE_FAIL_OPEN", False):
                res = await BarrikadeClient.scan_text("any input")
                assert res["is_safe"] is False


# Ingress Middleware Tests
def test_ingress_middleware_safe(client, agent_key_header):
    """Test safe ingress requests are allowed to proceed."""
    # With ingress disabled
    with patch("src.main.BARRIKADE_INGRESS_ENABLED", False):
        resp = client.get("/search?q=safe", headers=agent_key_header)
        assert resp.status_code == 200

    # With ingress enabled, safe scan verdict
    mock_scan = AsyncMock(
        return_value={
            "is_safe": True,
            "final_verdict": "pass",
            "decision_layer": "none",
            "confidence_score": 0.0,
            "error": None,
        }
    )
    with (
        patch("src.main.BARRIKADE_INGRESS_ENABLED", True),
        patch("src.main.BARRIKADE_URL", "http://mock-barrikade"),
        patch("src.barrikade_client.BarrikadeClient.scan_text", mock_scan),
    ):
        resp = client.get("/search?q=safe", headers=agent_key_header)
        assert resp.status_code == 200
        mock_scan.assert_called_once_with("safe")


def test_ingress_middleware_blocked_search(client, agent_key_header):
    """Test unsafe search queries are blocked with a 403 security violation."""
    mock_scan = AsyncMock(
        return_value={
            "is_safe": False,
            "final_verdict": "block",
            "decision_layer": "llm",
            "confidence_score": 0.98,
            "error": None,
        }
    )
    with (
        patch("src.main.BARRIKADE_INGRESS_ENABLED", True),
        patch("src.main.BARRIKADE_URL", "http://mock-barrikade"),
        patch("src.barrikade_client.BarrikadeClient.scan_text", mock_scan),
    ):
        resp = client.get("/search?q=unsafe-query", headers=agent_key_header)
        assert resp.status_code == 403
        data = resp.json()
        assert data["error"] == "security_violation"
        assert data["verdict"] == "block"
        assert data["decision_layer"] == "llm"
        assert data["confidence_score"] == 0.98


def test_ingress_middleware_blocked_workflow_body(client, agent_key_header):
    """Test unsafe workflow POST payloads are blocked with a 403."""
    mock_scan = AsyncMock(
        return_value={
            "is_safe": False,
            "final_verdict": "block",
            "decision_layer": "heuristic",
            "confidence_score": 0.85,
            "error": None,
        }
    )
    with (
        patch("src.main.BARRIKADE_INGRESS_ENABLED", True),
        patch("src.main.BARRIKADE_URL", "http://mock-barrikade"),
        patch("src.barrikade_client.BarrikadeClient.scan_text", mock_scan),
    ):
        resp = client.post(
            "/workflows/some-slug",
            json={"user_input": "malicious input here"},
            headers=agent_key_header,
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["error"] == "security_violation"
        mock_scan.assert_called_once_with("malicious input here")


# Egress Broker Tests
def test_egress_broker_safe(client, agent_key_header, barrikade_test_credentials):
    """Test safe broker egress requests are allowed."""
    mock_scan = AsyncMock(
        return_value={
            "is_safe": True,
            "final_verdict": "pass",
            "decision_layer": "none",
            "confidence_score": 0.0,
            "error": None,
        }
    )

    # We use simulate mode so we don't send real upstream requests
    with (
        patch("src.main.BARRIKADE_INGRESS_ENABLED", False),
        patch("src.routers.broker.BARRIKADE_EGRESS_ENABLED", True),
        patch("src.routers.broker.BARRIKADE_URL", "http://mock-barrikade"),
        patch("src.barrikade_client.BarrikadeClient.scan_text", mock_scan),
    ):
        resp = client.post(
            f"/{EGRESS_HOST}/v1/charges",
            json={"amount": 100, "description": "safe payment"},
            headers={**agent_key_header, "X-Jentic-Simulate": "true"},
        )
        assert resp.status_code == 200
        mock_scan.assert_any_call("safe payment")


def test_egress_broker_blocked(client, agent_key_header, barrikade_test_credentials):
    """Test unsafe broker egress requests are blocked before forwarding."""
    mock_scan = AsyncMock(
        return_value={
            "is_safe": False,
            "final_verdict": "block",
            "decision_layer": "llm",
            "confidence_score": 0.99,
            "error": None,
        }
    )

    with (
        patch("src.main.BARRIKADE_INGRESS_ENABLED", False),
        patch("src.routers.broker.BARRIKADE_EGRESS_ENABLED", True),
        patch("src.routers.broker.BARRIKADE_URL", "http://mock-barrikade"),
        patch("src.barrikade_client.BarrikadeClient.scan_text", mock_scan),
    ):
        resp = client.post(
            f"/{EGRESS_HOST}/v1/charges",
            json={"amount": 100, "description": "unsafe payment payload"},
            headers={**agent_key_header, "X-Jentic-Simulate": "true"},
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["error"] == "security_violation"
        assert data["verdict"] == "block"
        assert "unsafe payment payload" in mock_scan.call_args[0][0]
