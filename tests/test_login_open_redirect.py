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
    ],
)
def test_login_hostile_redirect_to_neutralized(admin_client, hostile):
    """Every known open-redirect bypass is rewritten to '/'."""
    resp = _post_login(admin_client, hostile)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/", (
        f"expected '/' for hostile input {hostile!r}, got {resp.headers['location']!r}"
    )
