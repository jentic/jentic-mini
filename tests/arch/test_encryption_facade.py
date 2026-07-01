"""Enforce that no module outside shared/crypto/encryption.py imports cryptography directly."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.arch.conftest import SRC_ROOT, python_files_in

ENCRYPTION_MODULE = SRC_ROOT / "shared" / "crypto" / "encryption.py"
SIGNING_MODULE = SRC_ROOT / "shared" / "crypto" / "signing.py"

FORBIDDEN_IMPORTS = {"cryptography"}


def _is_exempt(path: Path) -> bool:
    return path in (ENCRYPTION_MODULE, SIGNING_MODULE)


def _violating_imports(path: Path) -> list[str]:
    """Return forbidden import strings found in a source file."""
    source = path.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in FORBIDDEN_IMPORTS:
                    if alias.name == forbidden or alias.name.startswith(forbidden + "."):
                        violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for forbidden in FORBIDDEN_IMPORTS:
                if node.module == forbidden or node.module.startswith(forbidden + "."):
                    violations.append(node.module)
    return violations


@pytest.mark.arch
def test_no_direct_cryptography_imports():
    """No source file outside shared/crypto/encryption.py may import cryptography."""
    violations: list[tuple[str, list[str]]] = []
    for path in python_files_in(SRC_ROOT):
        if _is_exempt(path):
            continue
        found = _violating_imports(path)
        if found:
            rel = path.relative_to(SRC_ROOT)
            violations.append((str(rel), found))

    assert not violations, (
        "The following files import cryptography directly "
        "(use shared/crypto facade instead):\n"
        + "\n".join(f"  {f}: {imports}" for f, imports in violations)
    )
