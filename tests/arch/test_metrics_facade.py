"""Enforce that no module outside shared/metrics.py imports exporter packages directly."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.arch.conftest import SRC_ROOT, python_files_in

METRICS_MODULE = SRC_ROOT / "shared" / "metrics.py"

FORBIDDEN_IMPORTS = {
    "prometheus_client",
    "opentelemetry.exporter.prometheus",
    "opentelemetry.exporter.otlp.proto.grpc.metric_exporter",
    "opentelemetry.exporter.otlp.proto.http.metric_exporter",
}


def _is_exempt(path: Path) -> bool:
    return path == METRICS_MODULE


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
def test_no_direct_exporter_imports():
    """No source file outside shared/metrics.py may import exporter packages."""
    violations: list[tuple[str, list[str]]] = []
    for path in python_files_in(SRC_ROOT):
        if _is_exempt(path):
            continue
        found = _violating_imports(path)
        if found:
            rel = path.relative_to(SRC_ROOT)
            violations.append((str(rel), found))

    assert not violations, (
        "The following files import metrics exporter packages directly "
        "(use shared/metrics.py facade instead):\n"
        + "\n".join(f"  {f}: {imports}" for f, imports in violations)
    )
