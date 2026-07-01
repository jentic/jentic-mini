"""Tests for the search strategy registry."""

from __future__ import annotations

import pytest

from jentic_one.registry.repos.search import (
    SearchUnsupportedError,
    resolve_strategy,
)
from jentic_one.registry.repos.search.postgres_lexical import PostgresLexicalStrategy
from jentic_one.registry.repos.search.sqlite_lexical import SqliteLexicalStrategy
from jentic_one.shared.config import DatabaseConfig, SearchConfig
from jentic_one.shared.db.backends import get_backend


def test_postgres_lexical_resolves() -> None:
    backend = get_backend(DatabaseConfig(name="reg"))
    config = SearchConfig(search_mode="lexical")
    strategy = resolve_strategy(backend, config)
    assert isinstance(strategy, PostgresLexicalStrategy)
    assert strategy.name == "lexical"


def test_sqlite_lexical_resolves() -> None:
    backend = get_backend(DatabaseConfig(backend="sqlite", path=":memory:"))
    config = SearchConfig(search_mode="lexical")
    strategy = resolve_strategy(backend, config)
    assert isinstance(strategy, SqliteLexicalStrategy)
    assert strategy.name == "lexical"


def test_unknown_mode_raises() -> None:
    backend = get_backend(DatabaseConfig(name="reg"))
    config = SearchConfig(search_mode="lexical")
    # Hack the mode to test unknown lookup.
    object.__setattr__(config, "search_mode", "unknown_mode")
    with pytest.raises(SearchUnsupportedError, match="No search strategy"):
        resolve_strategy(backend, config)
