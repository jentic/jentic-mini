"""Shared URL utilities for server-variable substitution."""

from __future__ import annotations

from urllib.parse import quote


def apply_server_variables(url: str, variables: dict[str, str]) -> str:
    """Substitute OpenAPI server-variable values into a URL template.

    Each ``{name}`` placeholder in the URL is replaced with the URL-encoded
    value from *variables*. Unmatched placeholders (e.g. path parameters
    resolved elsewhere) are left intact.
    """
    result = url
    for name, value in variables.items():
        placeholder = "{" + name + "}"
        result = result.replace(placeholder, quote(value, safe=""))
    return result
