"""Unit tests for runner capability declaration + capability-gated composition (§11 RN-0.3).

The live HTTP-shaped runner declares a ``RunnerCapabilities`` profile, and
``build_runner`` only wraps a capability-gated layer (retry today) when the
transport supports it **and** the operator enabled it. A runner that declares no
capabilities (``capabilities_of`` default) is never wrapped in a gated layer.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from jentic_one.broker.adapters.runners.base import (
    HTTP_RUNNER_CAPABILITIES,
    RunnerRequest,
    RunnerResult,
    StreamingResult,
    capabilities_of,
)
from jentic_one.broker.adapters.runners.deadline import DeadlineRunner
from jentic_one.broker.adapters.runners.retry import RetryRunner
from jentic_one.broker.services.execution.pipeline import build_runner
from jentic_one.shared.broker.protocols import RunnerCapabilities, Verb
from jentic_one.shared.config import RetryConfig
from jentic_one.shared.models.credentials import CredentialType


def _ok() -> RunnerResult:
    return RunnerResult(status_code=200, body=b"ok", headers={}, content_type=None, duration_ms=1)


class _PlainRunner:
    """A bare runner with no ``capabilities()`` method (undeclared capabilities)."""

    async def run(self, request: RunnerRequest) -> RunnerResult:
        return _ok()


class _CapableRunner:
    """A runner that declares the supplied capability profile."""

    def __init__(self, caps: RunnerCapabilities) -> None:
        self._caps = caps

    def capabilities(self) -> RunnerCapabilities:
        return self._caps

    async def run(self, request: RunnerRequest) -> RunnerResult:
        return _ok()

    @contextlib.asynccontextmanager
    async def stream(self, request: RunnerRequest) -> AsyncIterator[StreamingResult]:
        yield StreamingResult(status_code=200, headers={}, content_type=None, aiter=_empty())


async def _empty() -> AsyncIterator[bytes]:
    return
    yield  # pragma: no cover


def _no_retry_caps() -> RunnerCapabilities:
    return RunnerCapabilities(
        verbs=frozenset({Verb.GET}),
        credential_types=frozenset({CredentialType.API_KEY}),
        one_shot_only=True,
        max_payload_bytes=0,
        supports_async=False,
        supports_idempotency=False,
        supports_retries=False,
    )


# --- capability declaration -----------------------------------------------------


def test_http_runner_capabilities_constant() -> None:
    caps = HTTP_RUNNER_CAPABILITIES
    assert caps.supports_retries
    assert caps.supports_idempotency
    assert caps.supports_async
    # HTTP injects every wire credential type (header/query/cookie).
    assert caps.credential_types == frozenset(CredentialType)
    assert Verb.POST in caps.verbs


def test_capabilities_of_declared_runner() -> None:
    caps = _no_retry_caps()
    assert capabilities_of(_CapableRunner(caps)) is caps


def test_capabilities_of_undeclared_runner_is_conservative() -> None:
    caps = capabilities_of(_PlainRunner())
    # An undeclared runner reports NO gated capabilities, so it is never wrapped.
    assert not caps.supports_retries
    assert not caps.supports_idempotency
    assert not caps.supports_async


# --- capability-gated composition ----------------------------------------------


def test_retry_applied_when_capable_and_enabled() -> None:
    runner = _CapableRunner(HTTP_RUNNER_CAPABILITIES)
    composed = build_runner(runner, deadline_s=5.0, retry=RetryConfig(enabled=True))

    assert isinstance(composed, DeadlineRunner)
    assert isinstance(composed._inner, RetryRunner)


def test_retry_skipped_when_runner_incapable() -> None:
    # Capable=False even though the operator enabled retry → not wrapped.
    runner = _CapableRunner(_no_retry_caps())
    composed = build_runner(runner, deadline_s=5.0, retry=RetryConfig(enabled=True))

    assert isinstance(composed, DeadlineRunner)
    assert composed._inner is runner


def test_retry_skipped_when_operator_disabled() -> None:
    runner = _CapableRunner(HTTP_RUNNER_CAPABILITIES)
    composed = build_runner(runner, deadline_s=5.0, retry=RetryConfig(enabled=False))

    assert isinstance(composed, DeadlineRunner)
    assert composed._inner is runner


def test_retry_skipped_for_undeclared_runner() -> None:
    # A bare runner with no capabilities() is treated as incapable.
    runner = _PlainRunner()
    composed = build_runner(runner, deadline_s=5.0, retry=RetryConfig(enabled=True))

    assert isinstance(composed, DeadlineRunner)
    assert composed._inner is runner


def test_explicit_caps_override_base_inspection() -> None:
    # The breaker-wrapped base declares nothing, but explicit caps say retries
    # are supported — mirrors the lifespan passing the inner HttpRunner's caps.
    breaker_like = _PlainRunner()
    composed = build_runner(
        breaker_like,
        deadline_s=5.0,
        retry=RetryConfig(enabled=True),
        caps=HTTP_RUNNER_CAPABILITIES,
    )

    assert isinstance(composed, DeadlineRunner)
    assert isinstance(composed._inner, RetryRunner)
    assert composed._inner._inner is breaker_like
