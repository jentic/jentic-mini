"""Enforce that argon2, jwt, and secrets are only imported in _support/."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from .conftest import SRC_ROOT

ADMIN_DIR = SRC_ROOT / "admin"
SUPPORT_DIR = ADMIN_DIR / "services" / "_support"

RESTRICTED_MODULES = frozenset({"argon2", "jwt", "secrets"})


def _check_file(filepath: Path) -> list[str]:
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_module = alias.name.split(".")[0]
                if top_module in RESTRICTED_MODULES:
                    violations.append(f"{filepath}:{node.lineno} — imports '{alias.name}'")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top_module = module.split(".")[0]
            if top_module in RESTRICTED_MODULES:
                violations.append(f"{filepath}:{node.lineno} — imports from '{module}'")

    return violations


@pytest.mark.arch
def test_admin_secrets_isolation() -> None:
    """argon2, jwt, and secrets must only be imported under admin/services/_support/."""
    violations: list[str] = []
    for py_file in ADMIN_DIR.rglob("*.py"):
        if py_file.is_relative_to(SUPPORT_DIR):
            continue
        violations.extend(_check_file(py_file))
    assert not violations, (
        "argon2, jwt, and secrets must only be imported in admin/services/_support/:\n"
        + "\n".join(violations)
    )
