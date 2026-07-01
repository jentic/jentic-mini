"""Enforce the service-layer list naming convention.

Service classes expose collection reads as ``list_all`` (optionally with more
specific variants like ``list_keys``), never a bare ``list``. A method named
exactly ``list`` shadows the built-in and is inconsistent with the repository
layer, which already standardises on ``list_all``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from .conftest import SRC_ROOT, python_files_in

SERVICE_DIRS = [
    SRC_ROOT / "admin" / "services",
    SRC_ROOT / "auth" / "services",
    SRC_ROOT / "broker" / "services",
    SRC_ROOT / "control" / "services",
    SRC_ROOT / "registry" / "services",
    SRC_ROOT / "shared" / "services",
]

FORBIDDEN_METHOD_NAME = "list"


def _check_file(filepath: Path) -> list[str]:
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or not node.name.endswith("Service"):
            continue
        for item in node.body:
            if (
                isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
                and item.name == FORBIDDEN_METHOD_NAME
            ):
                violations.append(
                    f"{filepath}:{item.lineno} — {node.name}.list is not allowed; "
                    f"name collection reads 'list_all'"
                )

    return violations


@pytest.mark.arch
def test_services_use_list_all_not_list() -> None:
    """Service classes must use ``list_all`` rather than a bare ``list`` method."""
    violations: list[str] = []
    for services_dir in SERVICE_DIRS:
        if not services_dir.exists():
            continue
        for py_file in python_files_in(services_dir):
            violations.extend(_check_file(py_file))
    assert not violations, (
        "Service classes must expose collection reads as 'list_all', not 'list':\n"
        + "\n".join(violations)
    )
