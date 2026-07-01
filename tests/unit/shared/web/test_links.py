"""Unit tests for the shared build_link helper."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.datastructures import URL

from jentic_one.shared.web.links import build_link


def _make_request(base_url: str) -> MagicMock:
    req = MagicMock()
    req.base_url = URL(base_url)
    return req


@pytest.mark.parametrize(
    ("base_url", "path", "expected"),
    [
        ("http://localhost:8000/", "/jobs/123", "http://localhost:8000/jobs/123"),
        ("http://localhost:8000", "/jobs/123", "http://localhost:8000/jobs/123"),
        ("http://localhost:8000/", "jobs/123", "http://localhost:8000/jobs/123"),
        ("http://localhost:8000", "jobs/123", "http://localhost:8000/jobs/123"),
        (
            "https://api.example.com/",
            "/inspect?id=GET%20https://foo.com/bar",
            "https://api.example.com/inspect?id=GET%20https://foo.com/bar",
        ),
        (
            "https://api.example.com/v1/",
            "/apis/vendor/name/1.0",
            "https://api.example.com/v1/apis/vendor/name/1.0",
        ),
    ],
)
def test_build_link(base_url: str, path: str, expected: str) -> None:
    request = _make_request(base_url)
    assert build_link(request, path) == expected
