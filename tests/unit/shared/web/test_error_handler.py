"""Unit tests for the shared make_service_error_handler factory."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import structlog.testing
from fastapi import Request
from fastapi.responses import JSONResponse

from jentic_one.shared.web.errors import make_service_error_handler


class _BaseServiceError(Exception):
    pass


class _NotFoundError(_BaseServiceError):
    pass


class _SubNotFoundError(_NotFoundError):
    """A subclass that is NOT in the error map — MRO walk should find parent."""

    pass


class _ServerError(_BaseServiceError):
    pass


class _UnmappedError(_BaseServiceError):
    pass


_ERROR_MAP: dict[type[Exception], tuple[int, str]] = {
    _NotFoundError: (404, "not_found"),
    _ServerError: (500, "server_error_mapped"),
}


def _make_request(path: str = "/test") -> MagicMock:
    request = MagicMock(spec=Request)
    request.url.path = path
    return request


@pytest.mark.asyncio
async def test_mapped_error_returns_correct_status_and_type() -> None:
    handler = make_service_error_handler(_ERROR_MAP)
    request = _make_request("/items/42")
    exc = _NotFoundError("Item 42 not found")

    response = await handler(request, exc)

    assert response.status_code == 404
    assert response.media_type == "application/problem+json"
    body: dict[str, object] = json.loads(bytes(response.body))
    assert body["type"] == "not_found"
    assert body["detail"] == "Item 42 not found"
    assert body["instance"] == "/items/42"


@pytest.mark.asyncio
async def test_unmapped_error_returns_500() -> None:
    handler = make_service_error_handler(_ERROR_MAP)
    request = _make_request("/something")
    exc = _UnmappedError("unexpected")

    response = await handler(request, exc)

    assert response.status_code == 500
    body: dict[str, object] = json.loads(bytes(response.body))
    assert body["type"] == "server_error"
    assert body["detail"] == "An unexpected error occurred"


@pytest.mark.asyncio
async def test_500_error_logged_at_error_level() -> None:
    handler = make_service_error_handler(_ERROR_MAP)
    request = _make_request("/ops")
    exc = _ServerError("disk full")

    with structlog.testing.capture_logs() as logs:
        response = await handler(request, exc)

    assert response.status_code == 500
    error_logs = [log for log in logs if log["log_level"] == "error"]
    assert len(error_logs) == 1
    assert error_logs[0]["event"] == "unhandled_service_error"
    assert error_logs[0]["status"] == 500
    assert error_logs[0]["type"] == "server_error_mapped"


@pytest.mark.asyncio
async def test_4xx_error_logged_at_warning_level() -> None:
    handler = make_service_error_handler(_ERROR_MAP)
    request = _make_request("/items/1")
    exc = _NotFoundError("gone")

    with structlog.testing.capture_logs() as logs:
        response = await handler(request, exc)

    assert response.status_code == 404
    warn_logs = [log for log in logs if log["log_level"] == "warning"]
    assert len(warn_logs) == 1
    assert warn_logs[0]["event"] == "client_error"
    assert warn_logs[0]["status"] == 404
    assert warn_logs[0]["type"] == "not_found"


@pytest.mark.asyncio
async def test_response_hook_is_called_and_can_mutate_headers() -> None:
    def hook(
        request: Request, exc: Exception, status_code: int, response: JSONResponse
    ) -> JSONResponse:
        response.headers["X-Custom"] = "added"
        return response

    handler = make_service_error_handler(_ERROR_MAP, response_hook=hook)
    request = _make_request("/items/1")
    exc = _NotFoundError("gone")

    response = await handler(request, exc)

    assert response.headers["X-Custom"] == "added"
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mro_walk_finds_parent_class_mapping() -> None:
    handler = make_service_error_handler(_ERROR_MAP)
    request = _make_request("/deep")
    exc = _SubNotFoundError("deep not found")

    response = await handler(request, exc)

    assert response.status_code == 404
    body: dict[str, object] = json.loads(bytes(response.body))
    assert body["type"] == "not_found"
    assert body["detail"] == "deep not found"
