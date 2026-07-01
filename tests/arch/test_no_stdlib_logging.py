"""Forbid stdlib ``logging.getLogger`` in application code.

The platform uses ``structlog`` for all structured logging — every module
acquires its logger via ``structlog.get_logger()``. Using the stdlib
``logging.getLogger`` produces unstructured output and bypasses the configured
processor chain.

The logging bootstrap (``shared/logging.py``) is exempt because it configures
the stdlib root logger that structlog routes through.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from .conftest import SRC_ROOT, python_files_in

ALLOWLIST = frozenset({SRC_ROOT / "shared" / "logging.py"})


def _calls_get_logger(node: ast.Call) -> bool:
    """Return True if *node* is a ``logging.getLogger(...)`` call."""
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "getLogger"
        and isinstance(func.value, ast.Name)
        and func.value.id == "logging"
    )


def _check_file(filepath: Path) -> list[str]:
    """Return violations for stdlib ``logging.getLogger`` usage."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _calls_get_logger(node):
            violations.append(
                f"{filepath}:{node.lineno} — stdlib 'logging.getLogger' is forbidden; "
                f"use 'structlog.get_logger()' instead"
            )

    return violations


@pytest.mark.arch
def test_no_stdlib_logging() -> None:
    """Application modules must use structlog, not stdlib ``logging.getLogger``."""
    violations: list[str] = []
    for py_file in python_files_in(SRC_ROOT):
        if py_file in ALLOWLIST:
            continue
        violations.extend(_check_file(py_file))
    assert not violations, (
        "Use structlog.get_logger() instead of stdlib logging.getLogger:\n" + "\n".join(violations)
    )
