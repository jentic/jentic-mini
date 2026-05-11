"""Three-mode integration tests for reverse-proxy path prefix support.

Mode A — JENTIC_ROOT_PATH unset, no X-Forwarded-Prefix → no mount (regression).
Mode B — JENTIC_ROOT_PATH=/foo simulated by setting app.root_path; FastAPI's
        per-request scope filling propagates this into scope["root_path"].
Mode C — X-Forwarded-Prefix: /foo header; ForwardedPrefixMiddleware reads it
        per-request and writes scope["root_path"].

All three modes are exercised against the same session-scoped `app` fixture.
A function-scoped fixture monkeypatches src.main.STATIC_DIR to point at
tests/fixtures/ so _render_index has an index.html to read regardless of
whether the UI build artefact is present.
"""

from pathlib import Path

import pytest


@pytest.fixture
def static_fixtures(monkeypatch):
    """Point STATIC_DIR at tests/fixtures/ for the duration of one test."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    monkeypatch.setattr("src.main.STATIC_DIR", fixtures_dir)
    return fixtures_dir


@pytest.fixture
def app_with_prefix(app, monkeypatch):
    """Mode B fixture — pin app.root_path so FastAPI fills scope["root_path"]."""
    monkeypatch.setattr(app, "root_path", "/foo")
    return app


# ── Mode A — unset, regression ──────────────────────────────────────────────


def test_mode_a_root_serves_unprefixed_base(client, static_fixtures):
    resp = client.get("/", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert b'href="/"' in resp.content
    assert b'href="/foo/"' not in resp.content


def test_mode_a_openapi_reachable(client, static_fixtures):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert "openapi" in resp.json()


def test_mode_a_docs_reachable(client, static_fixtures):
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert b"swagger-ui-bundle.js" in resp.content
    # Without a mount, asset URLs are bare (start with /static).
    assert b'src="/static/swagger-ui-bundle.js"' in resp.content


def test_mode_a_health_reachable(client, static_fixtures):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_mode_a_spa_fallback_for_credentials(client, static_fixtures):
    resp = client.get("/credentials", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert b'href="/"' in resp.content


def test_mode_a_login_cookie_path_unprefixed(admin_client, static_fixtures):
    """Login Set-Cookie carries Path=/ (no mount → origin-root cookie)."""
    resp = admin_client.post(
        "/user/login",
        json={"username": "testadmin", "password": "testpassword123"},
    )
    assert resp.status_code == 200
    cookie_header = resp.headers.get("set-cookie", "")
    assert "Path=/" in cookie_header
    assert "Path=/foo" not in cookie_header


# ── Mode B — env-pinned (app.root_path) ─────────────────────────────────────


def test_mode_b_root_serves_prefixed_base(client, app_with_prefix, static_fixtures):
    resp = client.get("/foo/", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert b'href="/foo/"' in resp.content


def test_mode_b_openapi_reachable(client, app_with_prefix, static_fixtures):
    """Proves task 6's path-strip propagates through APIKeyMiddleware._is_public."""
    resp = client.get("/foo/openapi.json")
    assert resp.status_code == 200
    assert "openapi" in resp.json()


def test_mode_b_docs_assets_prefixed(client, app_with_prefix, static_fixtures):
    """Hand-rolled /docs HTML embeds prefixed asset URLs."""
    resp = client.get("/foo/docs")
    assert resp.status_code == 200
    assert b"/foo/static/swagger-ui-bundle.js" in resp.content
    assert b"/foo/static/swagger-ui.css" in resp.content
    assert b'"/foo/openapi.json"' in resp.content
    assert b'href="/foo/login"' in resp.content


def test_mode_b_redoc_assets_prefixed(client, app_with_prefix, static_fixtures):
    resp = client.get("/foo/redoc")
    assert resp.status_code == 200
    assert b"/foo/static/redoc.standalone.js" in resp.content
    assert b"/foo/openapi.json" in resp.content


def test_mode_b_health_reachable(client, app_with_prefix, static_fixtures):
    resp = client.get("/foo/health")
    assert resp.status_code == 200


def test_mode_b_spa_fallback_for_credentials(client, app_with_prefix, static_fixtures):
    """Proves both task 6's path-strip AND task 9's <base> injection fire."""
    resp = client.get("/foo/credentials", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert b'href="/foo/"' in resp.content


def test_mode_b_login_cookie_path_prefixed(admin_client, app_with_prefix, static_fixtures):
    """Login Set-Cookie carries Path=/foo (cookie scoped to the mount)."""
    resp = admin_client.post(
        "/foo/user/login",
        json={"username": "testadmin", "password": "testpassword123"},
    )
    assert resp.status_code == 200
    cookie_header = resp.headers.get("set-cookie", "")
    assert "Path=/foo" in cookie_header


# ── Mode C — header-driven (X-Forwarded-Prefix) ─────────────────────────────


_PREFIX_HEADERS = {"X-Forwarded-Prefix": "/foo"}


def test_mode_c_root_serves_prefixed_base(client, static_fixtures):
    resp = client.get(
        "/foo/",
        headers={"Accept": "text/html", **_PREFIX_HEADERS},
    )
    assert resp.status_code == 200
    assert b'href="/foo/"' in resp.content


def test_mode_c_openapi_reachable(client, static_fixtures):
    resp = client.get("/foo/openapi.json", headers=_PREFIX_HEADERS)
    assert resp.status_code == 200
    assert "openapi" in resp.json()


def test_mode_c_docs_assets_prefixed(client, static_fixtures):
    resp = client.get("/foo/docs", headers=_PREFIX_HEADERS)
    assert resp.status_code == 200
    assert b"/foo/static/swagger-ui-bundle.js" in resp.content


def test_mode_c_health_reachable(client, static_fixtures):
    resp = client.get("/foo/health", headers=_PREFIX_HEADERS)
    assert resp.status_code == 200


def test_mode_c_spa_fallback_for_credentials(client, static_fixtures):
    resp = client.get(
        "/foo/credentials",
        headers={"Accept": "text/html", **_PREFIX_HEADERS},
    )
    assert resp.status_code == 200
    assert b'href="/foo/"' in resp.content


def test_mode_c_login_cookie_path_prefixed(admin_client, static_fixtures):
    """Mode C's load-bearing check: cookie Path is read from per-request scope.

    Proves the cookie-path lookup uses scope["root_path"] (set by the
    middleware from X-Forwarded-Prefix) rather than the static config value.
    """
    resp = admin_client.post(
        "/foo/user/login",
        json={"username": "testadmin", "password": "testpassword123"},
        headers=_PREFIX_HEADERS,
    )
    assert resp.status_code == 200
    cookie_header = resp.headers.get("set-cookie", "")
    assert "Path=/foo" in cookie_header


# ── Hostile X-Forwarded-Prefix is silently ignored ──────────────────────────


_HOSTILE_PREFIXES = (
    # Structural (kept from pre-allowlist era).
    "/foo bar",
    "/foo?x=1",
    "/foo/../bar",
    "//",
    "no-leading-slash",
    # Sink-reaching chars closed by the allowlist (PR #364 review).
    '/foo";alert(1);"',  # /docs inline-JS break-out
    "/foo<script>",  # HTML tag injection
    "/foo;Domain=evil.com",  # Set-Cookie attribute injection
    "/foo;SameSite=None",  # SameSite downgrade
    "/foo,bar",
    "/foo\x00bar",
)


def test_hostile_forwarded_prefix_is_ignored(client, static_fixtures):
    """Invalid X-Forwarded-Prefix values must not crash; treated as no mount."""
    for bad in _HOSTILE_PREFIXES:
        resp = client.get("/", headers={"Accept": "text/html", "X-Forwarded-Prefix": bad})
        assert resp.status_code == 200
        # Body has unprefixed base since the bad header was rejected.
        assert b'href="/"' in resp.content


def test_hostile_forwarded_prefix_does_not_reach_docs(client, static_fixtures):
    """Validator-rejected prefixes must not appear in the /docs HTML / inline JS."""
    for bad in _HOSTILE_PREFIXES:
        resp = client.get("/docs", headers={"X-Forwarded-Prefix": bad})
        assert resp.status_code == 200
        # The most weaponisable sink is the inline-JS string; assert it's clean.
        assert b'url: "/openapi.json"' in resp.content
        # The full hostile prefix must not appear anywhere in the response.
        # `/foo` substring is allowed (it's a legitimate path token); the
        # exploit needs the *trailing* attacker chars, so check the full value.
        assert bad.encode("latin-1") not in resp.content


def test_forwarded_prefix_disabled_by_env(client, static_fixtures, monkeypatch):
    """JENTIC_TRUST_FORWARDED_PREFIX=false → header is ignored, even when valid."""
    monkeypatch.setattr("src.main.JENTIC_TRUST_FORWARDED_PREFIX", False)
    resp = client.get(
        "/",
        headers={"Accept": "text/html", "X-Forwarded-Prefix": "/foo"},
    )
    assert resp.status_code == 200
    # With the fallback disabled, even a well-formed prefix is dropped.
    assert b'href="/"' in resp.content
    assert b'href="/foo/"' not in resp.content


def test_hostile_forwarded_prefix_does_not_reach_set_cookie(admin_client, static_fixtures):
    """Validator-rejected prefixes must not appear in the Set-Cookie Path attribute."""
    for bad in _HOSTILE_PREFIXES:
        resp = admin_client.post(
            "/user/login",
            json={"username": "testadmin", "password": "testpassword123"},
            headers={"X-Forwarded-Prefix": bad},
        )
        assert resp.status_code == 200
        cookie_header = resp.headers.get("set-cookie", "")
        # Rejected prefix → cookie scoped to "/" (no mount), one Path attribute.
        assert cookie_header.count("Path=") == 1
        assert "Path=/;" in cookie_header or cookie_header.endswith("Path=/")
        assert "Domain=" not in cookie_header
        assert "SameSite=strict" in cookie_header
