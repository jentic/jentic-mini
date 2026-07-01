"""Enforce that all admin service classes follow Style A: __init__(self, ctx: Context)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from .conftest import SRC_ROOT

SERVICES_DIR = SRC_ROOT / "admin" / "services"

SERVICE_FILES = [
    "auth_service.py",
    "event_service.py",
    "event_stream_service.py",
    "execution_service.py",
    "health_service.py",
    "invite_service.py",
    "job_result_service.py",
    "job_service.py",
    "permission_service.py",
    "user_service.py",
]


def _check_service_class(filepath: Path) -> list[str]:
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.name.endswith("Service"):
            continue

        init_found = False
        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef) and item.name == "__init__":
                init_found = True
                args = item.args
                params = [a.arg for a in args.args if a.arg != "self"]
                if params != ["ctx"]:
                    violations.append(
                        f"{filepath}:{item.lineno} — {node.name}.__init__ "
                        f"has params {params}, expected ['ctx']"
                    )
                ctx_annotation = args.args[1].annotation if len(args.args) > 1 else None
                if ctx_annotation is not None:
                    ann_name = ""
                    if isinstance(ctx_annotation, ast.Name):
                        ann_name = ctx_annotation.id
                    elif isinstance(ctx_annotation, ast.Attribute):
                        ann_name = ctx_annotation.attr
                    if ann_name != "Context":
                        violations.append(
                            f"{filepath}:{item.lineno} — {node.name}.__init__ "
                            f"ctx param annotated as '{ann_name}', expected 'Context'"
                        )

        if not init_found:
            violations.append(f"{filepath}:{node.lineno} — {node.name} has no __init__ method")

    return violations


@pytest.mark.arch
def test_admin_services_style_a() -> None:
    """Every service class must follow Style A: __init__(self, ctx: Context)."""
    violations: list[str] = []
    for filename in SERVICE_FILES:
        filepath = SERVICES_DIR / filename
        if filepath.exists():
            violations.extend(_check_service_class(filepath))
    assert not violations, (
        "Service classes must follow Style A (__init__(self, ctx: Context)):\n"
        + "\n".join(violations)
    )
