"""Unit tests for the build_canonical_url hostname fallback.

Regression for issue #378: when JENTIC_PUBLIC_BASE_URL is unset but
JENTIC_PUBLIC_HOSTNAME is set to a non-localhost value, build_canonical_url
must return a URL rooted at that hostname rather than deriving the host from
the inbound request headers. This ensures agents calling over docker-internal
DNS get a public success_redirect_uri that Pipedream can redirect browsers to.
"""

from __future__ import annotations

import importlib
import warnings

import pytest
import src.config
from src.config import normalise_public_hostname
from src.utils import build_canonical_url


class _FakeURL:
    scheme = "http"


class _FakeRequest:
    """Minimal request shape with an internal docker-DNS Host header."""

    def __init__(self, host: str = "jentic-mini-handle:8900", root_path: str = ""):
        self.headers = {"host": host}
        self.scope = {"root_path": root_path}
        self.url = _FakeURL()


# ── normalise_public_hostname ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Bare hostname — most common operator input.
        ("example.com", "example.com"),
        ("example.com:8900", "example.com:8900"),
        # Scheme accidentally included — strip it.
        ("https://example.com", "example.com"),
        ("http://example.com", "example.com"),
        ("https://example.com:8900", "example.com:8900"),
        # Trailing slash — strip it.
        ("example.com/", "example.com"),
        ("https://example.com/", "example.com"),
        # Path silently dropped — hostname is not a URL.
        ("example.com/some/path", "example.com"),
        ("https://example.com/some/path", "example.com"),
        # Empty / unset — defaults to localhost.
        ("", "localhost"),
        # localhost passthrough.
        ("localhost", "localhost"),
        ("localhost:8900", "localhost:8900"),
    ],
)
def test_normalise_public_hostname(raw, expected):
    assert normalise_public_hostname(raw) == expected


# ── Priority 1: JENTIC_PUBLIC_BASE_URL always wins ───────────────────────────


def test_base_url_wins_over_internal_host(monkeypatch):
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_BASE_URL", "https://x.example.com/jentic-mini")
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_HOSTNAME", "x.example.com")
    monkeypatch.setattr("src.utils.JENTIC_ROOT_PATH", "/jentic-mini")
    req = _FakeRequest(host="jentic-mini-handle:8900")
    assert (
        build_canonical_url(req, "/oauth-brokers/pipedream/connect-callback?app=gmail")
        == "https://x.example.com/jentic-mini/oauth-brokers/pipedream/connect-callback?app=gmail"
    )


def test_base_url_wins_over_spoofed_host_header(monkeypatch):
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_BASE_URL", "https://canonical.example.com")
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_HOSTNAME", "canonical.example.com")
    monkeypatch.setattr("src.utils.JENTIC_ROOT_PATH", "")
    req = _FakeRequest(host="attacker.example.com")
    assert build_canonical_url(req, "/path") == "https://canonical.example.com/path"


# ── Priority 2: JENTIC_PUBLIC_HOSTNAME fallback (non-localhost) ───────────────


def test_hostname_fallback_wins_over_spoofed_host_header(monkeypatch):
    """Core regression: docker-DNS / spoofed host must not bleed into the canonical URL."""
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_BASE_URL", "")
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_HOSTNAME", "x.example.com")
    monkeypatch.setattr("src.utils.JENTIC_ROOT_PATH", "")
    req = _FakeRequest(host="jentic-mini-handle:8900")
    assert (
        build_canonical_url(req, "/oauth-brokers/pipedream/connect-callback?app=gmail")
        == "https://x.example.com/oauth-brokers/pipedream/connect-callback?app=gmail"
    )


def test_hostname_fallback_includes_root_path(monkeypatch):
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_BASE_URL", "")
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_HOSTNAME", "x.example.com")
    monkeypatch.setattr("src.utils.JENTIC_ROOT_PATH", "/jentic-mini")
    req = _FakeRequest(host="jentic-mini-handle:8900")
    assert (
        build_canonical_url(req, "/oauth-brokers/pipedream/connect-callback?app=gmail")
        == "https://x.example.com/jentic-mini/oauth-brokers/pipedream/connect-callback?app=gmail"
    )


def test_hostname_fallback_uses_https(monkeypatch):
    """Scheme must always be https when synthesised from JENTIC_PUBLIC_HOSTNAME."""
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_BASE_URL", "")
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_HOSTNAME", "prod.example.com")
    monkeypatch.setattr("src.utils.JENTIC_ROOT_PATH", "")
    req = _FakeRequest(host="internal:8900")
    result = build_canonical_url(req, "/callback")
    assert result.startswith("https://")


# ── Priority 3: localhost dev fallback uses request headers ──────────────────


def test_localhost_dev_uses_request_headers(monkeypatch):
    """When JENTIC_PUBLIC_HOSTNAME is the default 'localhost', fall back to
    the request-derived URL so local dev ergonomics are preserved."""
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_BASE_URL", "")
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_HOSTNAME", "localhost")
    monkeypatch.setattr("src.utils.JENTIC_ROOT_PATH", "")
    req = _FakeRequest(host="localhost:8900")
    result = build_canonical_url(req, "/callback")
    assert "localhost" in result
    assert "internal" not in result


@pytest.mark.parametrize(
    "host_header,expected_prefix",
    [
        ("localhost:8900", "http://localhost:8900"),
        ("127.0.0.1:8900", "http://127.0.0.1:8900"),
    ],
)
def test_localhost_variants_fall_back_to_headers(monkeypatch, host_header, expected_prefix):
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_BASE_URL", "")
    monkeypatch.setattr("src.utils.JENTIC_PUBLIC_HOSTNAME", "localhost")
    monkeypatch.setattr("src.utils.JENTIC_ROOT_PATH", "")
    req = _FakeRequest(host=host_header)
    assert build_canonical_url(req, "/path").startswith(expected_prefix)


# ── Startup warning for _HOSTNAME-only deployments ───────────────────────────


def test_startup_warning_emitted_when_hostname_set_without_base_url(monkeypatch):
    """config.py must emit a UserWarning when JENTIC_PUBLIC_HOSTNAME is non-default
    but JENTIC_PUBLIC_BASE_URL is unset, so operators know canonical URLs assume https."""
    monkeypatch.setenv("JENTIC_PUBLIC_HOSTNAME", "prod.example.com")
    monkeypatch.delenv("JENTIC_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("JENTIC_ROOT_PATH", raising=False)
    # always filter so Python doesn't deduplicate across test runs in the same process
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        with pytest.warns(UserWarning, match="JENTIC_PUBLIC_BASE_URL"):
            importlib.reload(src.config)
    importlib.reload(src.config)  # restore defaults


def test_no_warning_when_base_url_set(monkeypatch):
    """No UserWarning emitted when JENTIC_PUBLIC_BASE_URL is explicitly set."""
    monkeypatch.setenv("JENTIC_PUBLIC_BASE_URL", "https://prod.example.com")
    monkeypatch.setenv("JENTIC_PUBLIC_HOSTNAME", "prod.example.com")
    monkeypatch.delenv("JENTIC_ROOT_PATH", raising=False)
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        importlib.reload(src.config)  # should not raise
    importlib.reload(src.config)  # restore defaults


def test_no_warning_for_localhost(monkeypatch):
    """No UserWarning emitted when JENTIC_PUBLIC_HOSTNAME is the default 'localhost'."""
    monkeypatch.delenv("JENTIC_PUBLIC_HOSTNAME", raising=False)
    monkeypatch.delenv("JENTIC_PUBLIC_BASE_URL", raising=False)
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        importlib.reload(src.config)  # should not raise
    importlib.reload(src.config)  # restore defaults
