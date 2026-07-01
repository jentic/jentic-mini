"""Forbid SQLAlchemy ``backref`` in ORM relationship definitions.

Relationships must be declared explicitly on both sides (or kept forward-only)
rather than using ``backref`` to implicitly create the reverse accessor.
Explicit ``back_populates`` makes the model graph readable and greppable.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from .conftest import SRC_ROOT, python_files_in


def _is_backref_call(node: ast.Call) -> bool:
    """Return True if *node* is a ``backref(...)`` call."""
    func = node.func
    if isinstance(func, ast.Name) and func.id == "backref":
        return True
    return isinstance(func, ast.Attribute) and func.attr == "backref"


def _uses_backref_kwarg(node: ast.Call) -> bool:
    """Return True if a relationship() call passes a ``backref=`` keyword."""
    func = node.func
    is_relationship = (isinstance(func, ast.Name) and func.id == "relationship") or (
        isinstance(func, ast.Attribute) and func.attr == "relationship"
    )
    if not is_relationship:
        return False
    return any(kw.arg == "backref" for kw in node.keywords)


def _check_file(filepath: Path) -> list[str]:
    """Return violations for any ``backref`` usage."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and (_is_backref_call(node) or _uses_backref_kwarg(node)):
            violations.append(
                f"{filepath}:{node.lineno} — 'backref' is forbidden; "
                f"declare relationships explicitly with 'back_populates'"
            )

    return violations


@pytest.mark.arch
def test_no_backref() -> None:
    """ORM models must not use SQLAlchemy ``backref``."""
    violations: list[str] = []
    for py_file in python_files_in(SRC_ROOT):
        violations.extend(_check_file(py_file))
    assert not violations, "Use back_populates instead of backref:\n" + "\n".join(violations)
