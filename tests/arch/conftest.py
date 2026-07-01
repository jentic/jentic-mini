"""Shared fixtures for architecture enforcement tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from tools.openapi_export import build_control_plane_spec

SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src" / "jentic_one"


def python_files_in(path: Path) -> Iterator[Path]:
    """Yield all .py files recursively under *path*."""
    yield from path.rglob("*.py")


@pytest.fixture(scope="session")
def generated_control_spec() -> dict[str, Any]:
    """The control-plane OpenAPI document, built once for the whole test session.

    Building the combined app and generating the schema for ~120 models is
    expensive under coverage tracing, so the OpenAPI arch tests share a single
    build instead of rebuilding per test.
    """
    return build_control_plane_spec()


@pytest.fixture()
def broker_source_dir() -> Path:
    return SRC_ROOT / "broker"


@pytest.fixture()
def control_source_dir() -> Path:
    return SRC_ROOT / "control"


@pytest.fixture()
def admin_source_dir() -> Path:
    return SRC_ROOT / "admin"


@pytest.fixture()
def registry_source_dir() -> Path:
    return SRC_ROOT / "registry"


@pytest.fixture()
def shared_source_dir() -> Path:
    return SRC_ROOT / "shared"


@pytest.fixture()
def auth_source_dir() -> Path:
    return SRC_ROOT / "auth"
