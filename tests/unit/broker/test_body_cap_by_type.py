"""Unit tests for the broker per-Content-Type request-body cap resolution (§04)."""

from __future__ import annotations

from jentic_one.broker.web.routers.execute import _resolve_body_cap
from jentic_one.shared.config import UpstreamClientConfig


def _cfg() -> UpstreamClientConfig:
    return UpstreamClientConfig(
        max_request_bytes=10 * 1024 * 1024,
        max_request_bytes_by_type={
            "application/json": 2 * 1024 * 1024,
            "multipart/form-data": 50 * 1024 * 1024,
            "audio/*": 20 * 1024 * 1024,
        },
    )


def test_exact_content_type_match() -> None:
    assert _resolve_body_cap("application/json", _cfg()) == 2 * 1024 * 1024
    assert _resolve_body_cap("multipart/form-data", _cfg()) == 50 * 1024 * 1024


def test_content_type_match_ignores_params_and_case() -> None:
    assert _resolve_body_cap("application/JSON; charset=utf-8", _cfg()) == 2 * 1024 * 1024


def test_wildcard_match() -> None:
    # audio/mpeg has no exact entry but matches the audio/* wildcard.
    assert _resolve_body_cap("audio/mpeg", _cfg()) == 20 * 1024 * 1024


def test_unknown_type_falls_back_to_global() -> None:
    assert _resolve_body_cap("image/png", _cfg()) == 10 * 1024 * 1024


def test_missing_type_falls_back_to_global() -> None:
    assert _resolve_body_cap(None, _cfg()) == 10 * 1024 * 1024
    assert _resolve_body_cap("", _cfg()) == 10 * 1024 * 1024
