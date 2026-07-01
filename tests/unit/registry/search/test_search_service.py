"""Tests for SearchService utilities — cursor encode/decode and relevance scoring."""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from typing import cast

import pytest

from jentic_one.registry.core.schema.operations import Operation
from jentic_one.registry.services.search_service import (
    _resolve_operation_url,
    compute_relevance_score,
)
from jentic_one.shared.pagination import (
    InvalidSearchCursorError,
    decode_search_cursor,
    encode_search_cursor,
)


def _operation(*, server_url: str | None, path: str) -> Operation:
    """A minimal Operation-like stub for `_resolve_operation_url`."""
    servers = [SimpleNamespace(url=server_url, variables=[])] if server_url is not None else []
    return cast(Operation, SimpleNamespace(servers=servers, version_servers=[], path=path))


def test_cursor_roundtrip() -> None:
    distance = 0.42
    op_id = "op-abc-123"
    encoded = encode_search_cursor(distance, op_id)
    decoded_dist, decoded_id = decode_search_cursor(encoded)
    assert abs(decoded_dist - distance) < 1e-10
    assert decoded_id == op_id


def test_cursor_roundtrip_zero() -> None:
    encoded = encode_search_cursor(0.0, "op-zero")
    dist, op_id = decode_search_cursor(encoded)
    assert dist == 0.0
    assert op_id == "op-zero"


def test_cursor_roundtrip_large() -> None:
    encoded = encode_search_cursor(1.999, "op-large")
    dist, op_id = decode_search_cursor(encoded)
    assert abs(dist - 1.999) < 1e-10
    assert op_id == "op-large"


def test_invalid_cursor_raises() -> None:
    with pytest.raises(InvalidSearchCursorError):
        decode_search_cursor("not-valid-base64!!")


def test_malformed_json_cursor_raises() -> None:
    bad = base64.b64encode(b"not json").decode()
    with pytest.raises(InvalidSearchCursorError):
        decode_search_cursor(bad)


def test_missing_key_cursor_raises() -> None:
    bad = base64.b64encode(json.dumps({"x": 1}).encode()).decode()
    with pytest.raises(InvalidSearchCursorError):
        decode_search_cursor(bad)


def test_relevance_distance_zero_gives_score_one() -> None:
    assert compute_relevance_score(0.0) == 1.0


def test_relevance_distance_one_gives_score_zero() -> None:
    assert compute_relevance_score(1.0) == 0.0


def test_relevance_distance_greater_than_one_clamps_to_zero() -> None:
    assert compute_relevance_score(1.5) == 0.0
    assert compute_relevance_score(2.0) == 0.0


def test_relevance_mid_distance() -> None:
    assert abs(compute_relevance_score(0.3) - 0.7) < 1e-10


# --- _resolve_operation_url: server/path join must match the broker URL index ---


def test_resolve_url_collapses_trailing_and_leading_slash() -> None:
    """Regression: a server ending in "/" + a path starting with "/" must NOT
    produce "host//path". That double slash never matched the broker's URL
    index, so the imported operation was unresolvable (e.g. Google Sheets:
    server "https://sheets.googleapis.com/" + path "/v4/..." → "...com//v4/...")."""
    op = _operation(server_url="https://sheets.googleapis.com/", path="/v4/spreadsheets/{id}")
    assert _resolve_operation_url(op) == "https://sheets.googleapis.com/v4/spreadsheets/{id}"


def test_resolve_url_inserts_missing_slash() -> None:
    op = _operation(server_url="https://api.example.com", path="v2/things")
    assert _resolve_operation_url(op) == "https://api.example.com/v2/things"


def test_resolve_url_single_slash_unchanged() -> None:
    op = _operation(server_url="https://api.example.com", path="/things")
    assert _resolve_operation_url(op) == "https://api.example.com/things"


def test_resolve_url_preserves_server_base_path() -> None:
    op = _operation(server_url="https://api.example.com/v2/", path="/things")
    assert _resolve_operation_url(op) == "https://api.example.com/v2/things"


def test_resolve_url_falls_back_to_path_without_servers() -> None:
    op = _operation(server_url=None, path="/v4/x")
    assert _resolve_operation_url(op) == "/v4/x"
