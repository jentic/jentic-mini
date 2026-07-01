"""Enforce that OTel instrumentation/propagation lives only in shared/tracing.py.

``shared/tracing.py`` is the single OTel *tracing* home (like ``shared/metrics.py``
for metrics): it owns the instrumentation imports **and** the span-attribute
redaction hooks. Centralising them there is a compliance guarantee — the broker
proxies ``Authorization``, injected API keys, cookies, and tenant bodies, and the
redaction hooks must not be forgotten by a new instrumentation site.

So no source module outside ``shared/tracing.py`` may import the OTel
``instrumentation`` packages or the propagator APIs directly. The plain tracing
**API** (``opentelemetry.trace`` — tracers/spans/status) stays allowed everywhere:
emitting spans is normal application code; wiring instrumentation is not.

``shared/web/app_factory.py`` is the **one** sanctioned exception: it owns the
process-wide FastAPI route-detail guard that patches an instrumentor internal,
and it calls the facade's ``instrument_inbound_app``/db instrumentors during app
startup. It must not, however, talk to the propagators directly.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.arch.conftest import SRC_ROOT, python_files_in

TRACING_MODULE = SRC_ROOT / "shared" / "tracing.py"
APP_FACTORY_MODULE = SRC_ROOT / "shared" / "web" / "app_factory.py"

# Wiring instrumentation + propagation belongs in the facade. The bare tracing
# API (opentelemetry.trace / .status) is intentionally NOT here — span emission
# is normal application code.
FORBIDDEN_PREFIXES = (
    "opentelemetry.instrumentation",
    "opentelemetry.propagate",
    "opentelemetry.propagators",
)

# app_factory owns the route-detail guard (an instrumentation internal) + calls
# the inbound/db instrumentors at startup, so it may import instrumentation —
# but never the propagators (those route through the facade's tracestate helper).
APP_FACTORY_ALLOWED_PREFIXES = ("opentelemetry.instrumentation",)


def _violating_imports(path: Path, allowed: tuple[str, ...]) -> list[str]:
    source = path.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    def _forbidden(name: str) -> bool:
        if any(name == a or name.startswith(a + ".") for a in allowed):
            return False
        return any(name == p or name.startswith(p + ".") for p in FORBIDDEN_PREFIXES)

    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(a.name for a in node.names if _forbidden(a.name))
        elif isinstance(node, ast.ImportFrom) and node.module and _forbidden(node.module):
            violations.append(node.module)
    return violations


@pytest.mark.arch
def test_no_direct_instrumentation_imports():
    """Only shared/tracing.py (and app_factory for instrumentation) may wire OTel."""
    violations: list[tuple[str, list[str]]] = []
    for path in python_files_in(SRC_ROOT):
        if path == TRACING_MODULE:
            continue
        allowed = APP_FACTORY_ALLOWED_PREFIXES if path == APP_FACTORY_MODULE else ()
        found = _violating_imports(path, allowed)
        if found:
            violations.append((str(path.relative_to(SRC_ROOT)), found))

    assert not violations, (
        "The following files import OTel instrumentation/propagator packages "
        "directly (use the shared/tracing.py facade instead):\n"
        + "\n".join(f"  {f}: {imports}" for f, imports in violations)
    )
