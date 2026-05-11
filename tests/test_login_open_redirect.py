"""Regression tests for the `redirect_to` parameter on POST /user/login.

CodeQL alert #663 (py/url-redirection, CWE-601): the prior guard required the
target to start with '/' and not '//', but missed that browsers normalize
backslashes to forward slashes per WHATWG URL parsing. That meant inputs like
'/\\evil.com' were interpreted as protocol-relative '//evil.com' once emitted
in the Location header, producing an open redirect.
"""

import pytest


_CREDS = {"username": "testadmin", "password": "testpassword123"}


def _post_login(admin_client, redirect_to):
    return admin_client.post(
        "/user/login",
        params={"redirect_to": redirect_to},
        json=_CREDS,
        follow_redirects=False,
    )


def test_login_no_redirect_returns_json(admin_client):
    """Sanity: login without redirect_to keeps the JSON 200 response."""
    resp = admin_client.post("/user/login", json=_CREDS, follow_redirects=False)
    assert resp.status_code == 200
    assert resp.json()["username"] == "testadmin"


def test_login_empty_redirect_to_returns_json(admin_client):
    """An empty redirect_to is falsy and must skip the redirect branch entirely."""
    resp = _post_login(admin_client, "")
    assert resp.status_code == 200
    assert resp.json()["username"] == "testadmin"


def test_login_safe_relative_path_passes_through(admin_client):
    resp = _post_login(admin_client, "/dashboard")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"


def test_login_root_path_passes_through(admin_client):
    resp = _post_login(admin_client, "/")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"


def test_login_safe_relative_path_with_query_passes_through(admin_client):
    resp = _post_login(admin_client, "/dashboard?tab=overview")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard?tab=overview"


@pytest.mark.parametrize(
    "hostile",
    [
        "https://evil.com",
        "http://evil.com/path",
        "//evil.com",
        "//evil.com/path",
        # Backslash bypasses — browsers normalize '\' to '/' per WHATWG URL spec.
        "/\\evil.com",
        "/\\\\evil.com",
        "\\\\evil.com",
        # Mixed-slash variants.
        "/\\/evil.com",
        # Scheme-only bypasses without leading slash.
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        # Leading whitespace fails startswith('/') check.
        " //evil.com",
        # Control characters — rejected at the validator boundary before
        # they ever reach the Location header, so the redirect falls back
        # to '/' just like every other hostile case.
        "/\r\n//evil.com",
        "/\r//evil.com",
        "/\n//evil.com",
        "/\t//evil.com",
    ],
)
def test_login_hostile_redirect_to_neutralized(admin_client, hostile):
    """Every known open-redirect bypass is rewritten to '/'."""
    resp = _post_login(admin_client, hostile)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/", (
        f"expected '/' for hostile input {hostile!r}, got {resp.headers['location']!r}"
    )


def test_login_redirect_to_blocked_emits_audit_log(admin_client, caplog):
    """Hostile inputs must produce a LOGIN_REDIRECT_BLOCKED warning on the
    `jentic.audit` logger so security teams can spot phishing probes.

    Also locks in that both user-controlled fields (username and redirect_to)
    are formatted via %r so repr() escapes any embedded control characters —
    %s would let a CRLF-laced value smuggle a fake log line.
    """
    with caplog.at_level("WARNING", logger="jentic.audit"):
        resp = _post_login(admin_client, "/\\evil.com")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
    blocked = [r for r in caplog.records if "LOGIN_REDIRECT_BLOCKED" in r.getMessage()]
    assert blocked, "expected a LOGIN_REDIRECT_BLOCKED audit-log line"
    msg = blocked[-1].getMessage()
    # %r renders the username as 'testadmin' (with quotes); %s would not.
    assert "user='testadmin'" in msg, f"username field not %r-formatted: {msg!r}"
    # No literal control chars anywhere in the message.
    assert "\r" not in msg and "\n" not in msg


def test_login_redirect_to_audit_log_truncates_long_input(admin_client, caplog):
    """A very long hostile redirect_to must be truncated in the audit log
    so probe traffic can't blow up log volume.
    """
    payload = "//" + ("A" * 5000)
    with caplog.at_level("WARNING", logger="jentic.audit"):
        resp = _post_login(admin_client, payload)
    assert resp.status_code == 303
    blocked = [r for r in caplog.records if "LOGIN_REDIRECT_BLOCKED" in r.getMessage()]
    assert blocked
    msg = blocked[-1].getMessage()
    # The logged %r of a truncated 200-char prefix is bounded; the full
    # 5000-char attacker payload must not appear verbatim.
    assert len(msg) < 500, f"audit message not truncated, length={len(msg)}"
    assert "A" * 500 not in msg
