"""Enforce pytest-style tests: no test classes (``class Test*``).

The project uses plain pytest functions with fixture injection rather than
xunit-style ``TestCase``/``class TestFoo`` groupings. Test classes encourage
shared mutable state and setup/teardown methods over fixtures.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).resolve().parent.parent


def _check_file(filepath: Path) -> list[str]:
    """Return violation messages for any top-level ``class Test*`` definitions."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    violations: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            violations.append(
                f"{filepath}:{node.lineno} — test class '{node.name}' is not allowed "
                f"(use top-level pytest functions with fixture injection)"
            )

    return violations


@pytest.mark.arch
def test_no_test_classes() -> None:
    """No test file may define a ``class Test*`` — use plain functions."""
    violations: list[str] = []
    for py_file in TESTS_ROOT.rglob("test_*.py"):
        violations.extend(_check_file(py_file))
    assert not violations, "Tests must be plain pytest functions, not classes:\n" + "\n".join(
        violations
    )
