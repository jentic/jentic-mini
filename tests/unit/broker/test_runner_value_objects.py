"""Unit tests for the transport-neutral runner value objects (RN-0.1).

These cover the foundation types in ``shared/broker/protocols.py`` that the later
§11 sub-PRs build on: the neutral :class:`Verb` vocabulary, the frozen/slotted
value objects, :class:`RunnerCapabilities`, and the :class:`PluggableUpstreamRunner`
protocol. They are pure unit tests — no DB, no network.
"""

from __future__ import annotations

import dataclasses
from enum import StrEnum

import pytest

from jentic_one.shared.broker import (
    EgressPolicy,
    PluggableUpstreamRunner,
    RunnerCapabilities,
    Target,
    UpstreamRequest,
    UpstreamResult,
    Verb,
)
from jentic_one.shared.models.credentials import CredentialType


def test_verb_is_a_strenum_with_neutral_members() -> None:
    assert issubclass(Verb, StrEnum)
    assert {v.value for v in Verb} >= {"get", "put", "post", "delete", "publish"}
    # A Verb is usable as a plain string (StrEnum): its value is the wire vocabulary.
    assert Verb.PUBLISH.value == "publish"
    assert Verb.GET.value == "get"
    assert isinstance(Verb.GET, str)


def test_target_is_frozen_and_slotted() -> None:
    target = Target(scheme="https", host="api.example.com", port=443, path="/v1/x")
    assert target.extra == {}
    assert not hasattr(target, "__dict__")  # slots=True
    with pytest.raises(dataclasses.FrozenInstanceError):
        target.host = "evil.example.com"  # type: ignore[misc]


def test_upstream_request_is_frozen_slotted_and_neutral() -> None:
    target = Target(scheme="https", host="api.example.com", path="/v1/x")
    req = UpstreamRequest(target=target, verb=Verb.POST, payload=b"body")
    assert req.options == {}
    # HTTP headers live in metadata as an HttpRunner detail, not a shared field.
    assert "headers" not in {f.name for f in dataclasses.fields(UpstreamRequest)}
    assert req.metadata == {}
    assert not hasattr(req, "__dict__")
    with pytest.raises(dataclasses.FrozenInstanceError):
        req.verb = Verb.GET  # type: ignore[misc]


def test_upstream_result_is_frozen_and_slotted() -> None:
    result = UpstreamResult(ok=True, code=200, payload=b"ok", content_type="text/plain")
    assert result.detail == {}
    assert not hasattr(result, "__dict__")
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.ok = False  # type: ignore[misc]


def test_runner_capabilities_holds_frozenset_typed_fields() -> None:
    caps = RunnerCapabilities(
        verbs=frozenset({Verb.GET, Verb.POST}),
        credential_types=frozenset({CredentialType.BEARER_TOKEN}),
        one_shot_only=False,
        max_payload_bytes=1024,
        supports_async=True,
        supports_idempotency=True,
        supports_retries=True,
    )
    assert isinstance(caps.verbs, frozenset)
    assert isinstance(caps.credential_types, frozenset)
    assert Verb.GET in caps.verbs
    assert CredentialType.BEARER_TOKEN in caps.credential_types
    assert not hasattr(caps, "__dict__")
    with pytest.raises(dataclasses.FrozenInstanceError):
        caps.supports_retries = False  # type: ignore[misc]


class _FakeEgressPolicy:
    """In-memory policy used to satisfy the protocol signature in tests."""

    def __init__(self) -> None:
        self.checked: list[Target] = []

    def check(self, target: Target) -> None:
        self.checked.append(target)


class _FakeRunner:
    """Minimal in-memory runner implementing :class:`PluggableUpstreamRunner`."""

    name = "fake"

    def __init__(self) -> None:
        self.started = False
        self.closed = False

    def capabilities(self) -> RunnerCapabilities:
        return RunnerCapabilities(
            verbs=frozenset({Verb.GET}),
            credential_types=frozenset(),
            one_shot_only=True,
            max_payload_bytes=0,
            supports_async=False,
            supports_idempotency=False,
            supports_retries=False,
        )

    async def startup(self) -> None:
        self.started = True

    async def aclose(self) -> None:
        self.closed = True

    def validate_target(self, req: UpstreamRequest, policy: EgressPolicy) -> None:
        policy.check(req.target)

    async def run(self, req: UpstreamRequest, credential: object | None) -> UpstreamResult:
        return UpstreamResult(ok=True, code=200, payload=b"", content_type=None)


def test_fake_runner_is_recognized_by_runtime_checkable_protocol() -> None:
    runner = _FakeRunner()
    assert isinstance(runner, PluggableUpstreamRunner)
    assert isinstance(_FakeEgressPolicy(), EgressPolicy)


@pytest.mark.asyncio
async def test_fake_runner_lifecycle_and_dispatch() -> None:
    runner = _FakeRunner()
    policy = _FakeEgressPolicy()
    target = Target(scheme="https", host="api.example.com", path="/v1/x")
    req = UpstreamRequest(target=target, verb=Verb.GET)

    await runner.startup()
    assert runner.started

    runner.validate_target(req, policy)
    assert policy.checked == [target]

    result = await runner.run(req, credential=None)
    assert result.ok
    assert result.code == 200

    await runner.aclose()
    assert runner.closed
