"""Enforce that JWKS key operations are consolidated in shared/auth/jwks.py."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.arch.conftest import SRC_ROOT, python_files_in

JWKS_MODULE = SRC_ROOT / "shared" / "auth" / "jwks.py"


def _imports_okp_algorithm(path: Path) -> bool:
    """Check if a file imports OKPAlgorithm from jwt.algorithms."""
    source = path.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "jwt.algorithms":
            for alias in node.names:
                if alias.name == "OKPAlgorithm":
                    return True
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "jwt.algorithms":
                    return True
    return False


@pytest.mark.arch
def test_okp_algorithm_only_in_jwks_module() -> None:
    """OKPAlgorithm must only be imported in shared/auth/jwks.py."""
    violations: list[str] = []
    for path in python_files_in(SRC_ROOT):
        if path == JWKS_MODULE:
            continue
        if _imports_okp_algorithm(path):
            violations.append(str(path.relative_to(SRC_ROOT)))

    assert not violations, (
        "OKPAlgorithm must only be imported in shared/auth/jwks.py, "
        "but was found in:\n" + "\n".join(f"  {f}" for f in violations)
    )


@pytest.mark.arch
def test_build_jwks_removed_from_id_token() -> None:
    """build_jwks must not exist in auth/core/id_token.py (moved to shared)."""
    id_token_path = SRC_ROOT / "auth" / "core" / "id_token.py"
    source = id_token_path.read_text()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "build_jwks":
            pytest.fail(
                "build_jwks() still exists in auth/core/id_token.py — use CachedJWKSPublisher"
            )
