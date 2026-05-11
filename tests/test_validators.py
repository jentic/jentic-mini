"""Unit tests for src.validators.

Pure-function tests — no HTTP, no DB. Integration coverage for the helper's
use sites lives in tests/test_login_open_redirect.py (login) and the OAuth
broker tests (return_to).
"""

import pytest
from src.validators import validate_relative_redirect


# ── validate_relative_redirect ───────────────────────────────────────────────


class TestValidateRelativeRedirect:
    @pytest.mark.parametrize(
        "target",
        [
            "/",
            "/dashboard",
            "/dashboard/sub/page",
            "/dashboard?tab=overview",
            "/dashboard?q=a&r=b",
            "/dashboard#anchor",
        ],
    )
    def test_safe_relative_paths_pass_through(self, target):
        assert validate_relative_redirect(target) == target

    def test_backslash_normalized_when_safe(self):
        # A backslash inside an otherwise-safe path is normalized to '/'
        # rather than rejected — keeps the redirect on-origin.
        assert validate_relative_redirect("/foo\\bar") == "/foo/bar"

    def test_single_leading_backslash_collapses_to_relative_path(self):
        # A single leading '\' becomes '/' after normalization — that's a
        # same-origin path, not a bypass. (Two backslashes WOULD be hostile,
        # because they collapse to protocol-relative '//evil.com' — covered
        # in test_hostile_inputs_rejected.)
        assert validate_relative_redirect("\\evil.com") == "/evil.com"

    @pytest.mark.parametrize("falsy", ["", None])
    def test_falsy_input_rejected(self, falsy):
        assert validate_relative_redirect(falsy) is None

    @pytest.mark.parametrize(
        "hostile",
        [
            # Schemed absolute URLs.
            "https://evil.com",
            "http://evil.com/path",
            "ftp://evil.com",
            # JavaScript / data URLs without a leading slash.
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            # Protocol-relative.
            "//evil.com",
            "//evil.com/path",
            # Backslash bypasses — browsers normalize '\' to '/' per WHATWG.
            "/\\evil.com",
            "/\\\\evil.com",
            "\\\\evil.com",
            "/\\/evil.com",
            # Non-slash starts.
            "evil.com",
            "../evil",
            "./foo",
            # Leading whitespace.
            " /foo",
            " //evil.com",
        ],
    )
    def test_hostile_inputs_rejected(self, hostile):
        assert validate_relative_redirect(hostile) is None

    @pytest.mark.parametrize(
        "ctrl",
        [
            "/foo\r",
            "/foo\n",
            "/foo\r\n//evil.com",
            "/foo\t",
            "/foo\x00",
            "\r/foo",
            "/\rfoo",
        ],
    )
    def test_control_chars_rejected(self, ctrl):
        # Defense in depth: even paths that look same-origin are rejected
        # if they contain ASCII control characters, to keep audit logs and
        # the Location header injection-safe.
        assert validate_relative_redirect(ctrl) is None
