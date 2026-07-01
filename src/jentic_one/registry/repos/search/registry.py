"""Strategy registry for search backends.

Maps (dialect, mode) pairs to SearchStrategy implementations.  Use
:func:`resolve_strategy` to obtain the correct strategy for the active
backend and configuration.
"""

from __future__ import annotations

from jentic_one.registry.repos.search.errors import SearchUnsupportedError
from jentic_one.registry.repos.search.protocol import SearchStrategy
from jentic_one.shared.config import SearchConfig
from jentic_one.shared.db.backends.base import DatabaseBackend

_STRATEGIES: dict[tuple[str, str], type[SearchStrategy]] = {}


def register_strategy[T: type[SearchStrategy]](cls: T) -> T:
    """Class decorator that registers a SearchStrategy by (dialect, name)."""
    key = (cls.dialect, cls.name)
    _STRATEGIES[key] = cls
    return cls


def resolve_strategy(backend: DatabaseBackend, config: SearchConfig) -> SearchStrategy:
    """Return an instantiated strategy for the given backend and config."""
    key = (backend.dialect_name, config.search_mode)
    strategy_cls = _STRATEGIES.get(key)
    if strategy_cls is None:
        available = [m for (d, m) in _STRATEGIES if d == backend.dialect_name]
        raise SearchUnsupportedError(
            f"No search strategy for ({backend.dialect_name}, {config.search_mode}). "
            f"Available modes for {backend.dialect_name}: {available}"
        )
    return strategy_cls()
