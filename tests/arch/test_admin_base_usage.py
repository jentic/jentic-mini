"""Ensure admin module models only inherit from AdminBase.

Models defined in the admin module must not use RegistryBase or ControlBase.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from .conftest import SRC_ROOT, python_files_in

WRONG_BASES = frozenset({"RegistryBase", "ControlBase"})


def _get_base_name(node: ast.expr) -> str | None:
    """Extract the base class name from a class definition base node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _find_wrong_base_classes(filepath: Path) -> list[str]:
    """Return violations for classes in admin that inherit from wrong bases."""
    source = filepath.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            name = _get_base_name(base)
            if name in WRONG_BASES:
                violations.append(
                    f"{filepath}:{node.lineno} — class {node.name} inherits from "
                    f"{name} (admin models must use AdminBase)"
                )
    return violations


@pytest.mark.arch
def test_admin_models_only_use_admin_base() -> None:
    """ORM models in the admin module must only inherit from AdminBase."""
    admin_dir = SRC_ROOT / "admin"
    violations: list[str] = []
    for py_file in python_files_in(admin_dir):
        violations.extend(_find_wrong_base_classes(py_file))
    assert not violations, "Admin models using wrong base class:\n" + "\n".join(violations)
