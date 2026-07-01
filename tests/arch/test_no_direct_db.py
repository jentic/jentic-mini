"""Ensure all modules with ORM models never import DB internals directly.

All database access must go through repository abstractions.
ORM model files (core/schema/) and repository files (repos/) are exempt.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from .conftest import python_files_in

SCHEMA_DIR = "core" + "/" + "schema"

FORBIDDEN_MODULES = frozenset(
    {
        "sqlalchemy",
        "asyncpg",
        "jentic_one.shared.db.session",
    }
)

FORBIDDEN_SYMBOLS = frozenset({"DatabaseSession"})


def _collect_imports(tree: ast.AST) -> list[tuple[str, int]]:
    """Return (module_or_symbol, lineno) for all imports in the AST."""
    results: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            results.append((module, node.lineno))
            for alias in node.names:
                results.append((alias.name, node.lineno))
    return results


def _check_file(filepath: Path) -> list[str]:
    """Return list of violation messages for a single file."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    violations: list[str] = []

    for name, lineno in _collect_imports(tree):
        for forbidden in FORBIDDEN_MODULES:
            if name == forbidden or name.startswith(f"{forbidden}."):
                violations.append(
                    f"{filepath}:{lineno} — imports '{name}' "
                    f"(direct DB access forbidden; use a repository layer)"
                )
        if name in FORBIDDEN_SYMBOLS:
            violations.append(
                f"{filepath}:{lineno} — imports symbol '{name}' "
                f"(direct DB access forbidden; use a repository layer)"
            )

    return violations


REPOS_DIR = "repos"
SCOPING_DIR = "scoping"


def _is_schema_file(filepath: Path) -> bool:
    """Return True if the file is an ORM schema definition (exempt from this rule)."""
    return SCHEMA_DIR in str(filepath)


def _is_repo_file(filepath: Path) -> bool:
    """Return True if the file is a repository implementation (legitimately imports sqlalchemy)."""
    return f"/{REPOS_DIR}/" in str(filepath) or str(filepath).endswith(f"/{REPOS_DIR}")


def _is_scoping_file(filepath: Path) -> bool:
    """Return True if the file is a scoping filter builder (produces query expressions)."""
    return f"/{SCOPING_DIR}/" in str(filepath)


@pytest.mark.arch
def test_broker_no_direct_db(broker_source_dir: Path) -> None:
    violations: list[str] = []
    for py_file in python_files_in(broker_source_dir):
        if _is_schema_file(py_file) or _is_repo_file(py_file) or _is_scoping_file(py_file):
            continue
        violations.extend(_check_file(py_file))
    assert not violations, "Broker module has forbidden DB imports:\n" + "\n".join(violations)


@pytest.mark.arch
def test_control_no_direct_db(control_source_dir: Path) -> None:
    violations: list[str] = []
    for py_file in python_files_in(control_source_dir):
        if _is_schema_file(py_file) or _is_repo_file(py_file) or _is_scoping_file(py_file):
            continue
        violations.extend(_check_file(py_file))
    assert not violations, "Control module has forbidden DB imports:\n" + "\n".join(violations)


@pytest.mark.arch
def test_registry_no_direct_db(registry_source_dir: Path) -> None:
    violations: list[str] = []
    for py_file in python_files_in(registry_source_dir):
        if _is_schema_file(py_file) or _is_repo_file(py_file) or _is_scoping_file(py_file):
            continue
        violations.extend(_check_file(py_file))
    assert not violations, "Registry module has forbidden DB imports:\n" + "\n".join(violations)


@pytest.mark.arch
def test_admin_no_direct_db(admin_source_dir: Path) -> None:
    violations: list[str] = []
    for py_file in python_files_in(admin_source_dir):
        if _is_schema_file(py_file) or _is_repo_file(py_file) or _is_scoping_file(py_file):
            continue
        violations.extend(_check_file(py_file))
    assert not violations, "Admin module has forbidden DB imports:\n" + "\n".join(violations)
