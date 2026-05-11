"""Unit tests for the path-prefix helpers — pure functions, no app fixture."""

import importlib

import pytest
import src.config
from src.config import normalise_root_path
from src.main import _inject_base_href  # noqa: PLC2701
from src.utils import build_absolute_url


# ── _inject_base_href ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "html,root_path,expected",
    [
        # No mount → bytes pass through unchanged.
        (b'<base href="/" />', "", b'<base href="/" />'),
        # Single-segment prefix.
        (b'<base href="/" />', "/foo", b'<base href="/foo/" />'),
        # Multi-segment prefix.
        (b'<base href="/" />', "/foo/bar", b'<base href="/foo/bar/" />'),
    ],
)
def test_inject_base_href_basic(html, root_path, expected):
    assert _inject_base_href(html, root_path) == expected


@pytest.mark.parametrize(
    "html",
    [
        b'<base href="/">',  # no self-close
        b'<base href="/"/>',  # self-close, no space
        b'<base href="/" >',  # trailing space inside
        b'<base  href="/"  />',  # double internal whitespace
    ],
)
def test_inject_base_href_formatting_drift(html):
    """Regex must absorb common formatting variants Vite emits."""
    out = _inject_base_href(html, "/foo")
    assert out == b'<base href="/foo/" />'


def test_inject_base_href_no_base_tag_returns_unchanged():
    """HTML without any <base> tag is returned unchanged — substitution is a no-op."""
    html = b"<!doctype html><html><head></head><body></body></html>"
    assert _inject_base_href(html, "/foo") == html


# ── normalise_root_path ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value",
    [
        "foo",  # no leading slash
        "/foo bar",  # whitespace
        "/foo?q=1",  # query
        "/foo#frag",  # fragment
        "/foo/../bar",  # parent traversal
        "//",  # double slash
        # Hostile chars covered by the allowlist — each would otherwise reach
        # an HTML attribute, inline JS string, or Set-Cookie attribute sink.
        '/foo"',  # double quote → JS-string / HTML-attr break-out
        "/foo'",  # single quote
        "/foo<script>",  # angle brackets → tag injection
        "/foo>bar",
        "/foo;Domain=evil.com",  # semicolon → cookie attribute injection
        "/foo,bar",
        "/foo\\bar",  # backslash
        "/foo\x00bar",  # NUL
        "/foo\x01bar",  # C0 control
        "/foo\x7fbar",  # DEL
        "/foo%20bar",  # percent-encoded — keep semantic chars out
        "/foo:bar",  # colon — defense vs. "looks like a URL scheme"
    ],
)
def test_normalise_root_path_invalid(value):
    with pytest.raises(RuntimeError, match="JENTIC_ROOT_PATH"):
        normalise_root_path(value)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", ""),
        ("/", ""),
        ("/foo", "/foo"),
        ("/foo/", "/foo"),
        ("/foo/bar", "/foo/bar"),
    ],
)
def test_normalise_root_path_valid(value, expected):
    assert normalise_root_path(value) == expected


# ── JENTIC_PUBLIC_BASE_URL vs JENTIC_ROOT_PATH sanity check ─────────────────


@pytest.mark.parametrize(
    "base_url,root_path",
    [
        # Paths agree — no error.
        ("https://example.com/foo", "/foo"),
        ("https://example.com/foo/bar", "/foo/bar"),
        # Both at origin root — no error.
        ("https://example.com", ""),
        ("https://example.com/", ""),
        ("https://example.com", "/"),
    ],
)
def test_public_base_url_root_path_match_is_ok(base_url, root_path, monkeypatch):

    monkeypatch.setenv("JENTIC_PUBLIC_BASE_URL", base_url)
    monkeypatch.setenv("JENTIC_ROOT_PATH", root_path)
    importlib.reload(src.config)  # should not raise


@pytest.mark.parametrize(
    "base_url,root_path",
    [
        ("https://example.com/foo", "/bar"),
        ("https://example.com/foo", ""),
        ("https://example.com", "/foo"),
    ],
)
def test_public_base_url_root_path_mismatch_raises(base_url, root_path, monkeypatch):

    monkeypatch.setenv("JENTIC_PUBLIC_BASE_URL", base_url)
    monkeypatch.setenv("JENTIC_ROOT_PATH", root_path)
    with pytest.raises(RuntimeError, match="JENTIC_PUBLIC_BASE_URL"):
        importlib.reload(src.config)


def test_public_base_url_unset_skips_check(monkeypatch):

    monkeypatch.delenv("JENTIC_PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("JENTIC_ROOT_PATH", "/foo")
    importlib.reload(src.config)  # should not raise even with root_path set


# ── build_absolute_url ───────────────────────────────────────────────────────


class _FakeURL:
    scheme = "http"


class _FakeRequest:
    """Minimal request shape for build_absolute_url unit tests."""

    def __init__(self, root_path: str = ""):
        self.headers = {"host": "example.com"}
        self.scope = {"root_path": root_path}
        self.url = _FakeURL()


def test_build_absolute_url_no_root_path():
    """Without a mount, the URL is host + path verbatim."""
    assert build_absolute_url(_FakeRequest(""), "/user/create") == "http://example.com/user/create"


def test_build_absolute_url_with_root_path():
    """Self-links emitted via build_absolute_url include scope['root_path']."""
    assert (
        build_absolute_url(_FakeRequest("/foo"), "/user/create")
        == "http://example.com/foo/user/create"
    )
