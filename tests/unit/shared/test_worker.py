"""Unit tests for the shared worker infrastructure."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from jentic_one.shared.config import WorkerConfig
from jentic_one.shared.jobs.handlers import JobHandlerRegistry, JobResultPayload
from jentic_one.shared.jobs.worker import WorkerLoop, _backoff_s
from jentic_one.shared.models.jobs import JobKind


class _FakeHandler:
    async def execute(
        self,
        job_id: str,
        session: Any,
        *,
        payload: dict[str, Any] | None = None,
        created_by: str | None = None,
        actor_type: str | None = None,
    ) -> JobResultPayload:
        return JobResultPayload(body={"done": True})


def test_register_and_get() -> None:
    registry = JobHandlerRegistry()
    handler = _FakeHandler()
    registry.register(JobKind.IMPORT, handler)
    assert registry.get(JobKind.IMPORT) is handler


def test_get_unregistered_returns_none() -> None:
    registry = JobHandlerRegistry()
    assert registry.get(JobKind.EXECUTION) is None


@pytest.mark.asyncio
async def test_claim_next_returns_none_when_no_handlers() -> None:
    """A worker with no registered handlers should never claim a job."""
    registry = JobHandlerRegistry()

    class _FakeDb:
        pass

    worker = WorkerLoop(db=_FakeDb(), handler_registry=registry, poll_interval=0.0)  # type: ignore[arg-type]
    result = await worker._claim_next()
    assert result is None


@pytest.mark.asyncio
async def test_run_survives_tick_exception() -> None:
    """A transient tick failure (e.g. cold-start DB error) must not kill the loop.

    The loop should log and keep polling rather than terminating permanently,
    which would otherwise leave every queued job stuck forever.
    """
    calls = 0

    class _FlakyWorker(WorkerLoop):
        def __init__(self) -> None:
            self._poll_interval = 0.0
            self._running = False

        async def _tick(self) -> bool:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("transient cold-start DB error")
            if calls >= 3:
                self._running = False
            return False

    worker = _FlakyWorker()
    await asyncio.wait_for(worker.run(), timeout=2.0)

    assert calls >= 3, "loop should keep ticking after a tick raised"


def test_backoff_grows_exponentially_and_caps() -> None:
    cfg = WorkerConfig(retry_backoff_base_s=2.0, retry_backoff_max_s=10.0)
    assert _backoff_s(1, cfg) == 2.0
    assert _backoff_s(2, cfg) == 4.0
    assert _backoff_s(3, cfg) == 8.0
    # 2 * 2**3 = 16 → capped at 10.
    assert _backoff_s(4, cfg) == 10.0
    assert _backoff_s(99, cfg) == 10.0


@pytest.mark.asyncio
async def test_drain_returns_immediately_when_idle() -> None:
    """drain() returns True at once when no job is in flight, and stops the loop."""

    class _FakeDb:
        pass

    worker = WorkerLoop(
        db=_FakeDb(),  # type: ignore[arg-type]
        handler_registry=JobHandlerRegistry(),
        worker_config=WorkerConfig(drain_timeout_s=1.0),
    )
    drained = await asyncio.wait_for(worker.drain(), timeout=1.0)
    assert drained is True
    assert worker._running is False
    assert worker._draining is True


@pytest.mark.asyncio
async def test_drain_stops_claiming_via_tick() -> None:
    """Once draining, _tick claims nothing even if handlers are registered."""

    class _FakeDb:
        pass

    worker = WorkerLoop(
        db=_FakeDb(),  # type: ignore[arg-type]
        handler_registry=_registry_with(_FakeHandler()),
        worker_config=WorkerConfig(),
    )
    worker._draining = True
    # _tick short-circuits before touching the DB while draining.
    assert await worker._tick() is False


def _registry_with(handler: Any) -> JobHandlerRegistry:
    reg = JobHandlerRegistry()
    reg.register(JobKind.EXECUTION, handler)
    return reg
