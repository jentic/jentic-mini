"""Lightweight liveness checks for deployed environments.

These tests cover an external (non-Helm) deployment where the broker and
control surfaces are reachable at fixed URLs. They auto-skip when those
URLs are not reachable (e.g. during the `make smoke-local` Helm-mode run,
where `tests/smoke/test_helm_modes.py` covers the cluster instead).
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest

from jentic_one.shared.config import load_config


def _is_reachable(url: str) -> bool:
    """Return True only if the URL serves an HTTP /health response.

    A plain TCP connect check is not enough: kind's `extraPortMappings`
    make the kind node listen on every mapped host port even when nothing
    inside the cluster is bound to the corresponding NodePort. Those
    sockets accept, then reset the HTTP request, which would falsely flip
    `_is_reachable -> True` in modes where a surface isn't deployed.
    Probing /health forces an actual HTTP roundtrip.
    """
    try:
        with urlopen(f"{url}/health", timeout=2) as resp:
            status: int = resp.status
            return 200 <= status < 500
    except (HTTPError, URLError, OSError, ConnectionResetError):
        return False


@pytest.mark.smoke
def test_broker_health(broker_url: str) -> None:
    if not _is_reachable(broker_url):
        pytest.skip(
            f"broker not reachable at {broker_url}; covered by test_helm_modes in cluster runs"
        )
    resp = urlopen(f"{broker_url}/health", timeout=5)
    assert resp.status == 200


@pytest.mark.smoke
def test_control_health(control_url: str) -> None:
    if not _is_reachable(control_url):
        pytest.skip(
            f"control not reachable at {control_url}; covered by test_helm_modes in cluster runs"
        )
    resp = urlopen(f"{control_url}/health", timeout=5)
    assert resp.status == 200


@pytest.mark.smoke
def test_config_loadable() -> None:
    config_file = os.environ.get("JENTIC_CONFIG_FILE")
    if config_file:
        assert Path(config_file).exists(), f"JENTIC_CONFIG_FILE={config_file} does not exist"
        load_config(Path(config_file))
    else:
        pytest.skip("JENTIC_CONFIG_FILE not set; skipping config load check")


@pytest.mark.smoke
def test_required_env_vars() -> None:
    mode = os.environ.get("MODE", "")
    if mode in ("combined", "parts", "broker"):
        pytest.skip("JENTIC_CONFIG_FILE not required in Helm mode (config via ConfigMaps)")
    required = ["JENTIC_CONFIG_FILE"]
    missing = [var for var in required if not os.environ.get(var)]
    assert not missing, f"Required environment variables not set: {missing}"
