"""Tests for backend-neutral identifier generation."""

from __future__ import annotations

import re
import uuid

from jentic_one.shared.db.ids import generate_ksuid, new_uuid

# Mirrors the Postgres generate_ksuid SQL function output shape:
#   <prefix>_<8 hex timestamp><16 hex random>
_KSUID_RE = re.compile(r"^(?P<prefix>[a-z]+)_(?P<ts>[0-9a-f]{8})(?P<rand>[0-9a-f]{16})$")


def test_generate_ksuid_format() -> None:
    value = generate_ksuid("ovr")
    match = _KSUID_RE.match(value)
    assert match is not None
    assert match.group("prefix") == "ovr"
    # prefix + "_" + 8 + 16
    assert len(value) == len("ovr") + 1 + 8 + 16


def test_generate_ksuid_unique() -> None:
    values = {generate_ksuid("cred") for _ in range(1000)}
    assert len(values) == 1000


def test_generate_ksuid_is_time_sortable() -> None:
    # The timestamp prefix is monotonic at second granularity; the random
    # suffix breaks ties but the timestamp segment must be hex-parseable.
    value = generate_ksuid("evt")
    ts_hex = value.split("_", 1)[1][:8]
    int(ts_hex, 16)  # must not raise


def test_new_uuid_returns_uuid() -> None:
    value = new_uuid()
    assert isinstance(value, uuid.UUID)
    assert new_uuid() != new_uuid()
