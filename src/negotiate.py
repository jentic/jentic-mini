"""
Content negotiation middleware for the Jentic Mini API.

Intercepts JSON responses and converts to YAML or Markdown based on the
request's Accept header. All existing routes get this automatically — no
changes to individual handlers required.

Supported media types:
  application/json       (default, no conversion)
  application/yaml
  text/yaml
  text/markdown
"""
import json
from typing import Any

import yaml
from fastapi import Request
from fastapi.responses import Response


# ---------------------------------------------------------------------------
# Accept header parsing
# ---------------------------------------------------------------------------

def _parse_accept(accept: str) -> str:
    """
    Return the best matching format given an Accept header value.
    Returns one of: 'json', 'yaml', 'markdown'.
    Respects q-values; ties broken in favour of the earlier entry.
    """
    items: list[tuple[float, str]] = []
    for part in accept.split(","):
        segments = [s.strip() for s in part.split(";")]
        mime = segments[0].lower()
        q = 1.0
        for seg in segments[1:]:
            if seg.startswith("q="):
                try:
                    q = float(seg[2:])
                except ValueError:
                    pass
        items.append((q, mime))

    # Stable sort — preserves input order for equal q-values.
    items.sort(key=lambda x: -x[0])

    for _, mime in items:
        if mime in ("text/yaml", "application/yaml", "application/x-yaml"):
            return "yaml"
        if mime == "text/markdown":
            return "markdown"
        if mime in ("application/json", "*/*", ""):
            return "json"

    return "json"


# ---------------------------------------------------------------------------
# Markdown rendering helpers
# ---------------------------------------------------------------------------

def _cell(value: Any, max_len: int = 80) -> str:
    """Render a value safely inside a Markdown table cell."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        s = json.dumps(value, ensure_ascii=False)
        return (s[:max_len] + "…") if len(s) > max_len else s
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(rows: list[dict]) -> str:
    """Render a homogeneous list of dicts as a GitHub-flavoured Markdown table."""
    keys: list[str] = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)

    header = "| " + " | ".join(keys) + " |"
    sep    = "| " + " | ".join("---" for _ in keys) + " |"
    body   = [
        "| " + " | ".join(_cell(row.get(k)) for k in keys) + " |"
        for row in rows
    ]
    return "\n".join([header, sep] + body) + "\n"


def _to_markdown(data: Any, depth: int = 1) -> str:
    """Recursively render arbitrary data as Markdown."""
    if data is None:
        return "_null_\n"
    if isinstance(data, bool):
        return ("true" if data else "false") + "\n"
    if isinstance(data, (int, float)):
        return str(data) + "\n"
    if isinstance(data, str):
        return data + "\n"

    if isinstance(data, list):
        if not data:
            return "_empty_\n"
        if all(isinstance(item, dict) for item in data):
            return _table(data)
        return "\n".join(f"- {_cell(item)}" for item in data) + "\n"

    if isinstance(data, dict):
        lines: list[str] = []
        h = "#" * min(depth, 6)
        for key, value in data.items():
            if isinstance(value, (dict, list)) and value:
                lines.append(f"{h} {key}")
                lines.append("")
                lines.append(_to_markdown(value, depth + 1).rstrip())
                lines.append("")
            else:
                lines.append(f"**{key}**: {_cell(value)}  ")
        return "\n".join(lines) + "\n"

    return str(data) + "\n"


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

async def negotiate_middleware(request: Request, call_next):
    """
    HTTP middleware: reformat JSON responses according to the Accept header.

    Passes through non-JSON responses (HTML, static assets, 204 No Content, etc.)
    without modification.
    """
    response = await call_next(request)

    # Only reformat if the route returned JSON.
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        return response

    accept = request.headers.get("accept", "application/json")
    target = _parse_accept(accept)

    if target == "json":
        return response  # No conversion needed — return as-is.

    # Drain the streaming body.
    body = b""
    async for chunk in response.body_iterator:
        body += chunk

    try:
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        # Couldn't parse — return the original bytes unchanged.
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

    if target == "yaml":
        content  = yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
        media    = "application/yaml; charset=utf-8"
    else:  # markdown
        content = _to_markdown(data)
        media   = "text/markdown; charset=utf-8"

    # Preserve all original headers except Content-Type and Content-Length
    # (both are regenerated by FastAPI's Response).
    keep = {
        k: v for k, v in response.headers.items()
        if k.lower() not in ("content-type", "content-length")
    }

    return Response(
        content=content,
        status_code=response.status_code,
        media_type=media,
        headers=keep,
    )
