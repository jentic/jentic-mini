"""Coverage / parity report between the reference and generated OpenAPI specs.

The hand-curated ``openapi/control/control.openapi.yaml`` is the metadata
reference. As metadata is ported into the FastAPI routers and Pydantic models,
this tool measures how much of that richness the *generated* spec now carries,
and lists what exists in one spec but not the other (both directions).

It is a burndown aid, not a CI gate (the drift test in
``tests/arch/test_openapi_conformance.py`` is the gate). Run::

    uv run python -m tools.openapi_parity                 # against checked-in file
    uv run python -m tools.openapi_parity --reference path/to/ref.yaml
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from tools.openapi_export import CONTROL_SPEC_PATH, build_control_plane_spec

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


@dataclass
class OperationCoverage:
    """Per-operation presence flags for the metadata we care about."""

    path: str
    method: str
    operation_id: bool = False
    summary: bool = False
    description: bool = False
    tags: bool = False
    response_examples: bool = False


@dataclass
class SchemaCoverage:
    """Per-schema presence flags for field-level documentation."""

    name: str
    described_fields: int = 0
    total_fields: int = 0
    has_examples: bool = False


@dataclass
class ParityReport:
    operations: list[OperationCoverage] = field(default_factory=list)
    schemas: list[SchemaCoverage] = field(default_factory=list)
    ops_only_in_reference: list[str] = field(default_factory=list)
    ops_only_in_generated: list[str] = field(default_factory=list)
    schemas_only_in_reference: list[str] = field(default_factory=list)
    schemas_only_in_generated: list[str] = field(default_factory=list)


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _operation_keys(spec: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method in item:
            if method.lower() in HTTP_METHODS:
                keys.add(f"{method.upper()} {path}")
    return keys


def _response_has_examples(operation: dict[str, Any]) -> bool:
    for response in (operation.get("responses") or {}).values():
        if not isinstance(response, dict):
            continue
        for content in (response.get("content") or {}).values():
            if not isinstance(content, dict):
                continue
            if content.get("example") is not None or content.get("examples"):
                return True
            schema = content.get("schema")
            if isinstance(schema, dict) and (
                schema.get("example") is not None or schema.get("examples")
            ):
                return True
    return False


def _collect_operation_coverage(spec: dict[str, Any]) -> list[OperationCoverage]:
    rows: list[OperationCoverage] = []
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            rows.append(
                OperationCoverage(
                    path=path,
                    method=method.upper(),
                    operation_id=bool(operation.get("operationId")),
                    summary=bool(operation.get("summary")),
                    description=bool(operation.get("description")),
                    tags=bool(operation.get("tags")),
                    response_examples=_response_has_examples(operation),
                )
            )
    return rows


def _collect_schema_coverage(spec: dict[str, Any]) -> list[SchemaCoverage]:
    rows: list[SchemaCoverage] = []
    schemas = (spec.get("components") or {}).get("schemas") or {}
    for name, schema in schemas.items():
        if not isinstance(schema, dict):
            continue
        properties = schema.get("properties") or {}
        described = sum(
            1 for prop in properties.values() if isinstance(prop, dict) and prop.get("description")
        )
        has_examples = bool(schema.get("examples") or schema.get("example")) or any(
            isinstance(prop, dict) and (prop.get("examples") or prop.get("example") is not None)
            for prop in properties.values()
        )
        rows.append(
            SchemaCoverage(
                name=name,
                described_fields=described,
                total_fields=len(properties),
                has_examples=has_examples,
            )
        )
    return rows


def build_report(reference: dict[str, Any], generated: dict[str, Any]) -> ParityReport:
    ref_ops = _operation_keys(reference)
    gen_ops = _operation_keys(generated)
    ref_schemas = set((reference.get("components") or {}).get("schemas") or {})
    gen_schemas = set((generated.get("components") or {}).get("schemas") or {})

    return ParityReport(
        operations=_collect_operation_coverage(generated),
        schemas=_collect_schema_coverage(generated),
        ops_only_in_reference=sorted(ref_ops - gen_ops),
        ops_only_in_generated=sorted(gen_ops - ref_ops),
        schemas_only_in_reference=sorted(ref_schemas - gen_schemas),
        schemas_only_in_generated=sorted(gen_schemas - ref_schemas),
    )


def _pct(part: int, whole: int) -> str:
    if whole == 0:
        return "n/a"
    return f"{100 * part / whole:.0f}%"


def format_report(report: ParityReport) -> str:
    lines: list[str] = []
    ops = report.operations
    n = len(ops)
    lines.append("=== Generated operation coverage ===")
    lines.append(f"operations: {n}")
    for label, attr in (
        ("operationId", "operation_id"),
        ("summary", "summary"),
        ("description", "description"),
        ("tags", "tags"),
        ("response examples", "response_examples"),
    ):
        have = sum(1 for op in ops if getattr(op, attr))
        lines.append(f"  {label:<18} {have}/{n} ({_pct(have, n)})")

    missing = [
        op
        for op in sorted(ops, key=lambda o: (o.path, o.method))
        if not (op.summary and op.description and op.response_examples and op.tags)
    ]
    if missing:
        lines.append("")
        lines.append("--- operations missing metadata (summary/desc/tags/examples) ---")
        for op in missing:
            gaps = [
                name
                for name, present in (
                    ("summary", op.summary),
                    ("description", op.description),
                    ("tags", op.tags),
                    ("examples", op.response_examples),
                    ("operationId", op.operation_id),
                )
                if not present
            ]
            lines.append(f"  {op.method:<6} {op.path}  -> missing: {', '.join(gaps)}")

    schemas = report.schemas
    described = sum(1 for s in schemas if s.total_fields and s.described_fields == s.total_fields)
    with_examples = sum(1 for s in schemas if s.has_examples)
    lines.append("")
    total = len(schemas)
    lines.append("=== Generated schema coverage ===")
    lines.append(f"schemas: {total}")
    lines.append(f"  fully field-described  {described}/{total} ({_pct(described, total)})")
    lines.append(f"  with examples          {with_examples}/{total} ({_pct(with_examples, total)})")

    lines.append("")
    lines.append("=== Drift between specs ===")
    lines.append(f"operations only in reference ({len(report.ops_only_in_reference)}):")
    lines.extend(f"  - {k}" for k in report.ops_only_in_reference)
    lines.append(f"operations only in generated ({len(report.ops_only_in_generated)}):")
    lines.extend(f"  + {k}" for k in report.ops_only_in_generated)
    lines.append(f"schemas only in reference ({len(report.schemas_only_in_reference)}):")
    lines.extend(f"  - {k}" for k in report.schemas_only_in_reference)
    lines.append(f"schemas only in generated ({len(report.schemas_only_in_generated)}):")
    lines.extend(f"  + {k}" for k in report.schemas_only_in_generated)
    return "\n".join(lines)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference",
        type=Path,
        default=CONTROL_SPEC_PATH,
        help="Reference spec to compare against (defaults to the checked-in control spec).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    reference = _load_yaml(args.reference)
    generated = build_control_plane_spec()
    report = build_report(reference, generated)
    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
