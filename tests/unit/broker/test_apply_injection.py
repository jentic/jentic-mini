"""Unit tests for ``_apply_injection`` — outbound auth application (§02b).

Query-param creds merge into the URL; cookie creds **append** to the inbound
``Cookie`` header without clobbering forwarded cookies; header creds pass through.
"""

from __future__ import annotations

from jentic_one.broker.web.routers.execute import _apply_injection
from jentic_one.shared.jobs.protocols import InjectedAuth


class _FakeRequest:
    def __init__(self, cookie: str | None = None) -> None:
        self._headers = {"cookie": cookie} if cookie is not None else {}

    @property
    def headers(self) -> dict[str, str]:
        return self._headers


def test_header_creds_pass_through() -> None:
    auth = InjectedAuth(headers={"X-Api-Key": "k"}, query_params={}, cookies={})
    url, headers = _apply_injection("https://api.x.com/v1", auth, _FakeRequest())  # type: ignore[arg-type]
    assert url == "https://api.x.com/v1"
    assert headers == {"X-Api-Key": "k"}


def test_query_creds_merge_into_url() -> None:
    auth = InjectedAuth(headers={}, query_params={"api_key": "k"}, cookies={})
    url, headers = _apply_injection(
        "https://api.x.com/v1?page=2",
        auth,
        _FakeRequest(),  # type: ignore[arg-type]
    )
    assert url == "https://api.x.com/v1?page=2&api_key=k"
    assert headers == {}


def test_cookie_creds_appended_to_existing_cookie() -> None:
    auth = InjectedAuth(headers={}, query_params={}, cookies={"session": "s"})
    url, headers = _apply_injection(
        "https://api.x.com/v1",
        auth,
        _FakeRequest(cookie="forwarded=1"),  # type: ignore[arg-type]
    )
    assert url == "https://api.x.com/v1"
    assert headers["Cookie"] == "forwarded=1; session=s"


def test_cookie_creds_set_when_no_inbound_cookie() -> None:
    auth = InjectedAuth(headers={}, query_params={}, cookies={"session": "s"})
    _, headers = _apply_injection("https://api.x.com/v1", auth, _FakeRequest())  # type: ignore[arg-type]
    assert headers["Cookie"] == "session=s"
