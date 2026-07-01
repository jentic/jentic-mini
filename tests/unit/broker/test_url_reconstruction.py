"""Unit tests for upstream URL reconstruction from the raw ASGI scope."""

from __future__ import annotations

from jentic_one.broker.core.proxy_headers import reconstruct_upstream_url


def _scope(raw_path: str, query_string: str = "") -> dict[str, object]:
    return {
        "raw_path": raw_path.encode("latin-1"),
        "query_string": query_string.encode("latin-1"),
    }


def test_bare_host_gets_https_scheme() -> None:
    url = reconstruct_upstream_url(_scope("/api.stripe.com/v1/charges"))
    assert url == "https://api.stripe.com/v1/charges"


def test_explicit_scheme_round_trips() -> None:
    url = reconstruct_upstream_url(_scope("/https://x/y"))
    assert url == "https://x/y"


def test_http_scheme_preserved() -> None:
    url = reconstruct_upstream_url(_scope("/http://example.com/p"))
    assert url == "http://example.com/p"


def test_query_string_reattached() -> None:
    url = reconstruct_upstream_url(_scope("/https://x/y", "a=1&b=2"))
    assert url == "https://x/y?a=1&b=2"


def test_encoded_slash_survives() -> None:
    # A single path segment containing a literal slash must NOT be collapsed.
    url = reconstruct_upstream_url(_scope("/https://api.github.com/repos/jentic%2Fcore"))
    assert url == "https://api.github.com/repos/jentic%2Fcore"
    assert "%2F" in url


def test_encoded_question_mark_survives_in_path() -> None:
    url = reconstruct_upstream_url(_scope("/https://x/a%3Fb"))
    assert "%3F" in url
