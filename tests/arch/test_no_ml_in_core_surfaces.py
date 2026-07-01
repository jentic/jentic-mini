"""Ensure core surfaces (broker, admin, control) never import ML embedding modules."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.arch.conftest import SRC_ROOT, python_files_in

ML_MODULES = {
    "sentence_transformers",
    "spacy",
    "torch",
    "jentic_one.registry.ingest.embeddings",
}


def _imports_from_file(path: Path) -> set[str]:
    """Extract all imported module names from a Python file."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


CORE_SURFACES = ["broker", "admin", "control"]


@pytest.mark.arch
@pytest.mark.parametrize("surface", CORE_SURFACES)
def test_core_surface_does_not_import_ml(surface: str):
    """Core surfaces must not import ML/embedding modules (they are registry-only)."""
    surface_dir = SRC_ROOT / surface
    if not surface_dir.exists():
        pytest.skip(f"{surface} surface not found")

    violations: list[str] = []
    for py_file in python_files_in(surface_dir):
        imports = _imports_from_file(py_file)
        for imp in imports:
            for ml_mod in ML_MODULES:
                if imp == ml_mod or imp.startswith(f"{ml_mod}."):
                    rel = py_file.relative_to(SRC_ROOT)
                    violations.append(f"{rel}: imports {imp}")

    assert not violations, (
        f"Surface '{surface}' must not import ML modules.\nViolations:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
