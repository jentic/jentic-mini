"""Enforce that test files never mock database internals.

All database interactions in tests must be against real databases.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from .conftest import python_files_in

TESTS_ROOT = Path(__file__).resolve().parent.parent

DB_SYMBOLS = frozenset(
    {
        "DatabaseSession",
        "AsyncSession",
        "create_async_engine",
        "asyncpg",
        "sqlalchemy",
    }
)


def _check_file(filepath: Path) -> list[str]:
    """Return violation messages if the file mocks DB-related symbols."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        target = _resolve_call_target(node)
        if target not in ("patch", "mock.patch", "unittest.mock.patch"):
            continue

        if not node.args:
            continue

        first_arg = node.args[0]
        if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
            continue

        patch_target = first_arg.value
        for symbol in DB_SYMBOLS:
            if symbol in patch_target:
                violations.append(
                    f"{filepath}:{node.lineno} — mocks '{patch_target}' "
                    f"(DB mocking forbidden; use real database connections)"
                )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        target = _resolve_call_target(node)
        if target in ("MagicMock", "AsyncMock", "Mock"):
            for kw in node.keywords:
                if kw.arg == "spec" and isinstance(kw.value, ast.Attribute):
                    attr_name = kw.value.attr
                    if attr_name in DB_SYMBOLS:
                        violations.append(
                            f"{filepath}:{node.lineno} — creates mock with spec={attr_name} "
                            f"(DB mocking forbidden; use real database connections)"
                        )

    return violations


def _resolve_call_target(node: ast.Call) -> str:
    """Resolve a Call node to a dotted name string."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        parts: list[str] = []
        current: ast.expr = node.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


@pytest.mark.arch
def test_no_db_mocking() -> None:
    """No test file should mock database internals."""
    violations: list[str] = []
    for py_file in python_files_in(TESTS_ROOT):
        if py_file.is_relative_to(TESTS_ROOT / "arch"):
            continue
        violations.extend(_check_file(py_file))
    assert not violations, (
        "Test files must not mock database internals — use real DB connections:\n"
        + "\n".join(violations)
    )
