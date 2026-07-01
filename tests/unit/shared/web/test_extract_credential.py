"""Unit tests for extract_credential()."""

from __future__ import annotations

from typing import cast

import httpx
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from jentic_one.shared.web.auth import extract_credential


def _make_request(headers: dict[str, str]) -> httpx.Response:
    app = FastAPI()

    @app.get("/test")
    async def _endpoint(request: Request) -> dict[str, str]:
        return {"credential": extract_credential(request)}

    client = TestClient(app)
    return cast(httpx.Response, client.get("/test", headers=headers))


def test_api_key_takes_precedence_over_bearer() -> None:
    resp = _make_request({"x-jentic-api-key": "jak_abc123", "Authorization": "Bearer some_token"})
    assert resp.status_code == 200
    assert resp.json()["credential"] == "jak_abc123"


def test_api_key_only() -> None:
    resp = _make_request({"x-jentic-api-key": "sak_xyz456"})
    assert resp.status_code == 200
    assert resp.json()["credential"] == "sak_xyz456"


def test_bearer_only() -> None:
    resp = _make_request({"Authorization": "Bearer my_token"})
    assert resp.status_code == 200
    assert resp.json()["credential"] == "my_token"


def test_neither_present_raises_unauthorized() -> None:
    resp = _make_request({})
    assert resp.status_code == 401


def test_malformed_auth_header_no_bearer_prefix() -> None:
    resp = _make_request({"Authorization": "Basic abc"})
    assert resp.status_code == 401
