"""Enforce that admin service modules do not import SQLAlchemy."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from .conftest import SRC_ROOT

SERVICES_DIR = SRC_ROOT / "admin" / "services"
SUPPORT_DIR = SERVICES_DIR / "_support"

FORBIDDEN_IMPORTS = frozenset({"sqlalchemy", "AsyncSession"})


def _check_file(filepath: Path) -> list[str]:
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(sym in alias.name for sym in FORBIDDEN_IMPORTS):
                    violations.append(f"{filepath}:{node.lineno} — imports '{alias.name}'")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if any(sym in module for sym in FORBIDDEN_IMPORTS):
                violations.append(f"{filepath}:{node.lineno} — imports from '{module}'")
            for alias in node.names:
                if alias.name in FORBIDDEN_IMPORTS:
                    violations.append(
                        f"{filepath}:{node.lineno} — imports '{alias.name}' from '{module}'"
                    )

    return violations


@pytest.mark.arch
def test_admin_services_no_sqlalchemy() -> None:
    """Service modules (excluding _support/) must not import sqlalchemy or AsyncSession."""
    violations: list[str] = []
    for py_file in SERVICES_DIR.rglob("*.py"):
        if py_file.is_relative_to(SUPPORT_DIR):
            continue
        violations.extend(_check_file(py_file))
    assert not violations, (
        "Admin service modules must not import sqlalchemy or AsyncSession:\n"
        + "\n".join(violations)
    )
