"""Unit tests for the per-caller rate limiter (§05 R2).

The limiter is a thin policy over the shared-state ``token_bucket``: one caller
flooding past its burst is denied with ``Retry-After`` while other callers are
unaffected; tokens refill over (injected) time so a denied caller recovers.
"""

from __future__ import annotations

import pytest

from jentic_one.shared.resilience import RateLimiter
from jentic_one.shared.state.backend import MemoryStateBackend


class _Clock:
    """Injectable monotonic clock for deterministic refill."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.mark.asyncio
async def test_burst_then_deny_with_retry_after() -> None:
    backend = MemoryStateBackend(clock=_Clock())
    # 60 rpm => 1 token/s refill; burst 3 means 3 immediate calls then deny.
    limiter = RateLimiter(backend, default_rpm=60, burst=3)

    for _ in range(3):
        assert (await limiter.acquire("agent-1")).allowed

    denied = await limiter.acquire("agent-1")
    assert not denied.allowed
    assert denied.limit == 3
    assert denied.remaining == 0
    # At 1 token/s a single-token deficit rounds up to a 1s Retry-After.
    assert denied.retry_after_s == 1
    headers = denied.headers()
    assert headers["RateLimit-Limit"] == "3"
    assert headers["RateLimit-Remaining"] == "0"


@pytest.mark.asyncio
async def test_other_callers_unaffected() -> None:
    backend = MemoryStateBackend(clock=_Clock())
    limiter = RateLimiter(backend, default_rpm=60, burst=2)

    assert (await limiter.acquire("agent-1")).allowed
    assert (await limiter.acquire("agent-1")).allowed
    assert not (await limiter.acquire("agent-1")).allowed

    # A different actor has a full, independent bucket.
    assert (await limiter.acquire("agent-2")).allowed
    assert (await limiter.acquire("agent-2")).allowed


@pytest.mark.asyncio
async def test_recovers_after_refill() -> None:
    clock = _Clock()
    backend = MemoryStateBackend(clock=clock)
    limiter = RateLimiter(backend, default_rpm=60, burst=1)

    assert (await limiter.acquire("agent-1")).allowed
    assert not (await limiter.acquire("agent-1")).allowed

    clock.advance(1.0)  # 1 token refilled at 1 token/s
    assert (await limiter.acquire("agent-1")).allowed
