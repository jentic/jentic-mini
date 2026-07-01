"""Unit tests for the state backend factory + fail-fast config."""

from __future__ import annotations

import pytest
import structlog.testing
from pydantic import SecretStr

from jentic_one.shared.state import (
    BackendKind,
    MemoryStateBackend,
    StateBackendConfig,
    build_state_backend,
)


def test_memory_is_default() -> None:
    backend = build_state_backend(StateBackendConfig())
    assert isinstance(backend, MemoryStateBackend)


def test_memory_explicit() -> None:
    backend = build_state_backend(StateBackendConfig(backend=BackendKind.MEMORY))
    assert isinstance(backend, MemoryStateBackend)


def test_redis_without_url_fails_fast() -> None:
    cfg = StateBackendConfig(backend=BackendKind.REDIS, redis_url=None)
    with pytest.raises(RuntimeError, match="redis_url"):
        build_state_backend(cfg)


def test_redis_default_prefix_warns() -> None:
    """Selecting redis with the unchanged default prefix emits a startup warning."""
    cfg = StateBackendConfig(
        backend=BackendKind.REDIS, redis_url=SecretStr("redis://localhost:6379/0")
    )
    with structlog.testing.capture_logs() as logs:
        backend = build_state_backend(cfg)
    assert backend is not None
    assert any("default key prefix" in entry.get("event", "") for entry in logs)


def test_redis_custom_prefix_does_not_warn() -> None:
    cfg = StateBackendConfig(
        backend=BackendKind.REDIS,
        redis_url=SecretStr("redis://localhost:6379/0"),
        redis_key_prefix="jentic:broker:prod:",
    )
    with structlog.testing.capture_logs() as logs:
        build_state_backend(cfg)
    assert not any("default key prefix" in entry.get("event", "") for entry in logs)


def test_backend_kind_values() -> None:
    assert BackendKind.MEMORY.value == "memory"
    assert BackendKind.REDIS.value == "redis"
