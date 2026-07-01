"""Smoke tests for local Helm/kind deployments across modes."""

from __future__ import annotations

import json
import subprocess
from urllib.request import urlopen

import pytest


@pytest.mark.smoke
def test_health_combined(base_url: str, mode: str) -> None:
    if mode != "combined":
        pytest.skip("only applies in combined mode")
    resp = urlopen(f"{base_url}/health", timeout=5)
    assert resp.status == 200


@pytest.mark.smoke
def test_health_surfaces(mode: str, registry_url: str, admin_url: str, control_url: str) -> None:
    if mode != "parts":
        pytest.skip("only applies in parts mode")
    # In parts mode each surface is a standalone app at root ("/health"), not
    # a path prefix on a single host. Hit each surface on its own URL.
    for name, url in (
        ("registry", registry_url),
        ("admin", admin_url),
        ("control", control_url),
    ):
        resp = urlopen(f"{url}/health", timeout=5)
        assert resp.status == 200, f"{name} health check failed at {url}"


@pytest.mark.smoke
def test_broker_health(base_url: str, broker_url: str, mode: str) -> None:
    if mode not in ("combined", "broker"):
        pytest.skip("only applies in combined or broker mode")
    resp = urlopen(f"{broker_url}/health", timeout=5)
    assert resp.status == 200


@pytest.mark.smoke
def test_pods_ready(mode: str) -> None:
    result = subprocess.run(
        [
            "kubectl",
            "get",
            "pods",
            "-n",
            "jentic",
            "-l",
            "app.kubernetes.io/instance=jentic",
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        pytest.skip("kubectl not available or cluster not running")
    pods = json.loads(result.stdout)
    items = pods.get("items", [])
    assert len(items) > 0, f"No pods found for mode={mode}"

    for pod in items:
        name = pod["metadata"]["name"]
        phase = pod.get("status", {}).get("phase", "")

        if phase == "Failed":
            pytest.fail(f"Job pod {name} is in Failed phase")

        # Job pods transition to Succeeded after completion — they never report Ready
        if phase == "Succeeded":
            continue

        conditions = pod.get("status", {}).get("conditions", [])
        ready = any(c["type"] == "Ready" and c["status"] == "True" for c in conditions)
        assert ready, f"Pod {name} is not Ready (phase={phase})"
