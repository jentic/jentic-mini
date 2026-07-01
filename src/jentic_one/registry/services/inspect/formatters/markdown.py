"""Render an OperationInspectResult as Markdown."""

from __future__ import annotations

import json
from typing import Any

from jentic_one.registry.services.inspect.models import OperationInspectResult


def render_markdown(result: OperationInspectResult) -> str:
    """Render an operation inspect result as markdown documentation."""
    return _render_operation_markdown(result)


def _render_operation_markdown(result: OperationInspectResult) -> str:
    lines: list[str] = []
    title = result.name or f"{result.method} {result.url}"
    lines.append(f"# {title}")
    lines.append("")

    if result.description:
        lines.append(result.description)
        lines.append("")

    lines.append(f"**Method:** `{result.method}`")
    lines.append(f"**URL:** `{result.url}`")
    if result.server:
        lines.append(f"**Server:** `{result.server}`")
    lines.append("")

    lines.append(f"**API:** {result.api.vendor}/{result.api.name} {result.api.version}")
    if result.api.description:
        lines.append(f"> {result.api.description}")
    lines.append("")

    if result.parameters:
        lines.append("## Parameters")
        lines.append("")
        _describe_params(lines, result.parameters)
        lines.append("")

    if result.response_schema:
        lines.append("## Response Schema")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(result.response_schema, indent=2))
        lines.append("```")
        lines.append("")

    if result.auth:
        lines.append("## Authentication")
        lines.append("")
        for auth in result.auth:
            lines.append(f"- **{auth.type}**")
            if auth.scheme:
                lines.append(f"  - Scheme: `{auth.scheme}`")
            if auth.in_location and auth.param_name:
                lines.append(f"  - In: `{auth.in_location}` (`{auth.param_name}`)")
            if auth.bearer_format:
                lines.append(f"  - Bearer format: `{auth.bearer_format}`")
        lines.append("")

    return "\n".join(lines)


def _describe_params(lines: list[str], params: dict[str, object]) -> None:
    for name, schema in params.items():
        type_str = _schema_type(schema) if isinstance(schema, dict) else "unknown"
        desc = ""
        if isinstance(schema, dict):
            desc = _describe_field(schema)
        lines.append(f"- `{name}` ({type_str}){desc}")


def _describe_field(schema: dict[str, Any]) -> str:
    desc = schema.get("description", "")
    if desc:
        return f" — {desc}"
    return ""


def _schema_type(schema: Any) -> str:
    if isinstance(schema, dict):
        return str(schema.get("type", "object"))
    return "unknown"
