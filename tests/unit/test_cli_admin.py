"""Unit tests for the ``jentic_one`` CLI glue (create-admin / reset-password).

The underlying ``AuthService`` methods are covered by integration tests; this
file pins the CLI-specific seam that ``jenticctl`` pipes into — argument
dispatch, stdin password reading on the non-interactive path, the
password-mismatch / too-short pre-checks, and the exception→exit-code mapping —
none of which the Go layer can reach. ``AuthService`` and ``Context`` are
patched so no database is required.
"""

from __future__ import annotations

import io
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jentic_one import __main__ as cli
from jentic_one.admin.services.errors import (
    AdminServiceError,
    SetupAlreadyCompleteError,
    UserEmailNotFoundError,
)

_VALID_PW = "a-strong-passw0rd"  # pragma: allowlist secret  (>= 12 chars)
_SHORT_PW = "short"  # pragma: allowlist secret


@contextmanager
def _patched_auth_service(svc: MagicMock):
    """Patch out config/logging/Context and inject a fake AuthService.

    ``Context`` is used as an async context manager in the CLI, so the patched
    instance must support ``async with``; ``AuthService(ctx)`` returns ``svc``.
    """

    class _FakeContext:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None: ...

        async def __aenter__(self) -> _FakeContext:
            return self

        async def __aexit__(self, *_exc: object) -> bool:
            return False

    with (
        patch.object(cli, "load_config", return_value=MagicMock()),
        patch.object(cli, "configure_logging"),
        patch.object(cli, "Context", _FakeContext),
        patch.object(cli, "AuthService", return_value=svc),
    ):
        yield


def _run(argv: list[str], svc: MagicMock, stdin: str = "") -> int:
    """Invoke ``main(argv)`` with a fake service and a non-TTY stdin."""
    fake_stdin = io.StringIO(stdin)
    fake_stdin.isatty = lambda: False  # type: ignore[method-assign]
    with _patched_auth_service(svc), patch("jentic_one.__main__.sys.stdin", fake_stdin):
        return cli.main(argv)


# ── create-admin ────────────────────────────────────────────────────────────


def test_create_admin_success_reads_password_from_stdin() -> None:
    svc = MagicMock()
    svc.bootstrap_admin = AsyncMock()
    rc = _run(["create-admin", "--email", "founder@local"], svc, stdin=f"{_VALID_PW}\n")
    assert rc == 0
    svc.bootstrap_admin.assert_awaited_once()
    assert svc.bootstrap_admin.await_args.kwargs["password"] == _VALID_PW
    assert svc.bootstrap_admin.await_args.kwargs["email"] == "founder@local"


def test_create_admin_short_password_exits_2_without_calling_service() -> None:
    svc = MagicMock()
    svc.bootstrap_admin = AsyncMock()
    rc = _run(["create-admin", "--email", "founder@local", "--password", _SHORT_PW], svc)
    assert rc == 2
    svc.bootstrap_admin.assert_not_awaited()


def test_create_admin_setup_already_complete_exits_3() -> None:
    svc = MagicMock()
    svc.bootstrap_admin = AsyncMock(side_effect=SetupAlreadyCompleteError())
    rc = _run(["create-admin", "--email", "founder@local", "--password", _VALID_PW], svc)
    assert rc == 3


def test_create_admin_generic_service_error_exits_1() -> None:
    svc = MagicMock()
    svc.bootstrap_admin = AsyncMock(side_effect=AdminServiceError("boom"))
    rc = _run(["create-admin", "--email", "founder@local", "--password", _VALID_PW], svc)
    assert rc == 1


# ── reset-password ───────────────────────────────────────────────────────────


def test_reset_password_success_reads_password_from_stdin() -> None:
    svc = MagicMock()
    svc.reset_password = AsyncMock(return_value="usr_123")
    rc = _run(["reset-password", "--email", "user@local"], svc, stdin=f"{_VALID_PW}\n")
    assert rc == 0
    svc.reset_password.assert_awaited_once_with(email="user@local", temporary_password=_VALID_PW)


def test_reset_password_short_password_exits_2_without_calling_service() -> None:
    svc = MagicMock()
    svc.reset_password = AsyncMock()
    rc = _run(["reset-password", "--email", "user@local", "--password", _SHORT_PW], svc)
    assert rc == 2
    svc.reset_password.assert_not_awaited()


def test_reset_password_unknown_email_exits_3() -> None:
    svc = MagicMock()
    svc.reset_password = AsyncMock(side_effect=UserEmailNotFoundError("nobody@local"))
    rc = _run(["reset-password", "--email", "nobody@local", "--password", _VALID_PW], svc)
    assert rc == 3


def test_reset_password_generic_service_error_exits_1() -> None:
    svc = MagicMock()
    svc.reset_password = AsyncMock(side_effect=AdminServiceError("boom"))
    rc = _run(["reset-password", "--email", "user@local", "--password", _VALID_PW], svc)
    assert rc == 1


@pytest.mark.parametrize("command", ["create-admin", "reset-password"])
def test_empty_email_exits_2(command: str) -> None:
    svc = MagicMock()
    svc.bootstrap_admin = AsyncMock()
    svc.reset_password = AsyncMock()
    # --email "" is empty after strip → email-required guard fires before any
    # service call (password is supplied so it can't short-circuit first).
    rc = _run([command, "--email", "", "--password", _VALID_PW], svc)
    assert rc == 2
