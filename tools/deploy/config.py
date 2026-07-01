"""Constants and path helpers for the deploy CLI."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

IMG_PREFIX = "jentic-one"
SERVICES = ("app", "registry", "admin", "control", "broker")
MODE_SERVICES: dict[str, tuple[str, ...]] = {
    "combined": ("app", "broker"),
    "parts": ("registry", "admin", "control", "broker"),
    "broker": ("broker",),
}

KIND_CLUSTER = "jentic-local"
NAMESPACE = "jentic"
RELEASE = "jentic"
OBS_RELEASE = "obs"
MONITORING_NS = "monitoring"
HELM_TIMEOUT = "5m"

HELM_DIR = REPO_ROOT / "deploy" / "helm"
VALUES_DIR = HELM_DIR / "values"


def get_version() -> str:
    """Read the project version via scripts/version.sh."""
    result = subprocess.run(
        [str(REPO_ROOT / "scripts" / "version.sh")],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def mode_values_file(mode: str) -> Path:
    return VALUES_DIR / f"local-{mode}.yaml"


def otel_values_file() -> Path:
    return VALUES_DIR / "local-otel-app.yaml"


def prom_values_file() -> Path:
    return VALUES_DIR / "local-prom-app.yaml"


def obs_values_file() -> Path:
    return VALUES_DIR / "local-observability.yaml"
