"""Unit tests for the idempotency request fingerprint (§07 §1).

The fingerprint is the stable identity of a request under a given
``Idempotency-Key``: the same logical request must hash identically (so a retry
*replays*), while any change to method, URL, toolkit, or body must change the
hash (so a key reuse for a *different* request is a 409 conflict). Volatile
headers are deliberately excluded.
"""

from __future__ import annotations

from jentic_one.broker.core.idempotency import fingerprint


def test_identical_requests_match() -> None:
    a = fingerprint("POST", "https://api.example.com/v1/charge", "stripe", b'{"amt":100}')
    b = fingerprint("POST", "https://api.example.com/v1/charge", "stripe", b'{"amt":100}')
    assert a == b


def test_method_is_case_insensitive() -> None:
    lower = fingerprint("post", "https://api.example.com/x", "tk", b"")
    upper = fingerprint("POST", "https://api.example.com/x", "tk", b"")
    assert lower == upper


def test_different_method_differs() -> None:
    get = fingerprint("GET", "https://api.example.com/x", "tk", b"")
    put = fingerprint("PUT", "https://api.example.com/x", "tk", b"")
    assert get != put


def test_different_url_differs() -> None:
    a = fingerprint("POST", "https://api.example.com/a", "tk", b"")
    b = fingerprint("POST", "https://api.example.com/b", "tk", b"")
    assert a != b


def test_different_toolkit_differs() -> None:
    a = fingerprint("POST", "https://api.example.com/x", "stripe", b"")
    b = fingerprint("POST", "https://api.example.com/x", "adyen", b"")
    assert a != b


def test_different_body_differs() -> None:
    a = fingerprint("POST", "https://api.example.com/x", "tk", b'{"amt":100}')
    b = fingerprint("POST", "https://api.example.com/x", "tk", b'{"amt":200}')
    assert a != b


def test_none_body_equals_empty_body() -> None:
    none = fingerprint("POST", "https://api.example.com/x", "tk", None)
    empty = fingerprint("POST", "https://api.example.com/x", "tk", b"")
    assert none == empty


def test_field_boundaries_are_unambiguous() -> None:
    # A NUL separator means concatenation can't collide: "a"+"b" must not equal
    # "ab"+"" across adjacent fields.
    a = fingerprint("GET", "https://x/ab", "", b"")
    b = fingerprint("GET", "https://x/a", "b", b"")
    assert a != b
