"""Unit tests for the boundary-safe provider config store decoder.

``provider_config_store._decode`` must be dialect-agnostic: Postgres
JSON/JSONB returns a parsed object, while SQLite stores JSON as text and
returns a string. Both must normalize to a dict; anything else is an error.
"""

from __future__ import annotations

import pytest

from jentic_one.shared.provider_config_store import _decode


def test_decode_passes_through_dict() -> None:
    """A pre-parsed object (Postgres JSON/JSONB) is returned as-is."""
    obj = {"kind": "pipedream", "client_id": "abc"}
    assert _decode(obj) == obj


def test_decode_parses_json_string() -> None:
    """A JSON string (SQLite text storage) is parsed into a dict."""
    assert _decode('{"kind": "pipedream", "client_id": "abc"}') == {
        "kind": "pipedream",
        "client_id": "abc",
    }


@pytest.mark.parametrize("raw", ['"a string"', "[1, 2, 3]", "42", "null"])
def test_decode_rejects_non_object_json(raw: str) -> None:
    """JSON that doesn't decode to an object is a hard error."""
    with pytest.raises(ValueError, match="must decode to an object"):
        _decode(raw)


def test_decode_rejects_non_dict_object() -> None:
    with pytest.raises(ValueError, match="must decode to an object"):
        _decode([1, 2, 3])
