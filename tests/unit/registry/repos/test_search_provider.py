"""Tests for search strategy resolution."""

from __future__ import annotations

from jentic_one.registry.repos.search import resolve_strategy
from jentic_one.registry.repos.search.postgres_lexical import PostgresLexicalStrategy
from jentic_one.registry.repos.search.sqlite_lexical import SqliteLexicalStrategy
from jentic_one.shared.config import DatabaseConfig, SearchConfig
from jentic_one.shared.db.backends import get_backend


def test_postgres_backend_selects_lexical_strategy() -> None:
    backend = get_backend(DatabaseConfig(name="reg"))
    config = SearchConfig(search_mode="lexical")
    strategy = resolve_strategy(backend, config)
    assert isinstance(strategy, PostgresLexicalStrategy)


def test_sqlite_backend_selects_lexical_strategy() -> None:
    backend = get_backend(DatabaseConfig(backend="sqlite", path=":memory:"))
    config = SearchConfig(search_mode="lexical")
    strategy = resolve_strategy(backend, config)
    assert isinstance(strategy, SqliteLexicalStrategy)
