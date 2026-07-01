"""Regression test for the OTel FastAPI route-detail guard.

OpenTelemetry's ``_get_route_details`` reads ``route.path`` while walking
``app.routes``. FastAPI wraps ``include_router`` results in an opaque
``_IncludedRouter`` with no ``path``; upstream only guards the ``Match.FULL``
branch, so a request that path-matches an included router without matching a
method (a CORS ``OPTIONS`` preflight, a ``405``) used to raise ``AttributeError``
and 500. ``_install_otel_route_detail_guard`` makes the lookup crash-safe.
"""

from __future__ import annotations

from typing import Any, ClassVar

import opentelemetry.instrumentation.fastapi as otel_fastapi
import pytest
from starlette.routing import Match

import jentic_one.shared.web.app_factory as app_factory


class _IncludedRouterLike:
    """Mimics FastAPI's ``_IncludedRouter``: partial-matches, exposes no ``path``."""

    def matches(self, scope: dict[str, Any]) -> tuple[Match, dict[str, Any]]:
        return Match.PARTIAL, {}


class _App:
    routes: ClassVar[list[_IncludedRouterLike]] = [_IncludedRouterLike()]


def test_route_detail_guard_survives_partial_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_factory, "_otel_route_guard_installed", False)
    original = otel_fastapi._get_route_details
    try:
        app_factory._install_otel_route_detail_guard()
        scope = {"type": "http", "method": "OPTIONS", "path": "/auth/login", "app": _App()}
        get_details: Any = otel_fastapi._get_route_details
        # Without the guard this raises AttributeError -> 500 at request time.
        assert get_details(scope) == "/auth/login"
    finally:
        otel_fastapi._get_route_details = original


def test_route_detail_guard_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_factory, "_otel_route_guard_installed", False)
    original = otel_fastapi._get_route_details
    try:
        app_factory._install_otel_route_detail_guard()
        wrapped = otel_fastapi._get_route_details
        app_factory._install_otel_route_detail_guard()
        # Second call is a no-op: the function is not re-wrapped.
        assert otel_fastapi._get_route_details is wrapped
    finally:
        otel_fastapi._get_route_details = original
