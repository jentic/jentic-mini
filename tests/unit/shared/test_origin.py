"""Tests for the Origin enum and derive_origin helper."""

import pytest

from jentic_one.shared.models.actors import Origin
from jentic_one.shared.web.deps import derive_origin


def test_origin_values() -> None:
    assert Origin.CLI.value == "cli"
    assert Origin.DASHBOARD.value == "dashboard"
    assert Origin.API.value == "api"
    assert Origin.AGENT.value == "agent"
    assert Origin.SYSTEM.value == "system"


def test_origin_string_serialization() -> None:
    assert str(Origin.CLI) == "cli"
    assert str(Origin.DASHBOARD) == "dashboard"


def test_origin_all_members() -> None:
    assert set(Origin) == {
        Origin.CLI,
        Origin.DASHBOARD,
        Origin.API,
        Origin.AGENT,
        Origin.SYSTEM,
    }


def test_derive_origin_cli_prefix() -> None:
    assert derive_origin("jentic-cli/1.0.0") == Origin.CLI


def test_derive_origin_cli_prefix_case_insensitive() -> None:
    assert derive_origin("Jentic-CLI/2.3.1") == Origin.CLI


def test_derive_origin_mozilla_prefix() -> None:
    assert derive_origin("Mozilla/5.0 (Windows NT 10.0; rv:109.0)") == Origin.DASHBOARD


def test_derive_origin_applewebkit_prefix() -> None:
    assert derive_origin("AppleWebKit/537.36 (KHTML, like Gecko)") == Origin.DASHBOARD


def test_derive_origin_unknown_user_agent() -> None:
    assert derive_origin("python-httpx/0.24.0") == Origin.API


def test_derive_origin_empty_user_agent() -> None:
    assert derive_origin("") == Origin.API


def test_derive_origin_none_user_agent() -> None:
    assert derive_origin(None) == Origin.API


@pytest.mark.parametrize(
    "ua",
    [
        "curl/7.81.0",
        "PostmanRuntime/7.32.2",
        "httpie/3.2.1",
    ],
)
def test_derive_origin_generic_tools_default_to_api(ua: str) -> None:
    assert derive_origin(ua) == Origin.API
