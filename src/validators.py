"""
Input normalisation helpers for Jentic Mini.

NormModel  — base class: strips whitespace from every string field before validation.
NormStr    — Annotated type: strips + lowercases (use for enum-like fields: type, effect…).
TrimStr    — Annotated type: strips only (use where case matters: name, label, URL…).
strip_param / norm_param — normalise optional query-parameter strings.
"""

from typing import Annotated, Any, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, model_validator
from pydantic.functional_validators import BeforeValidator


# ---------------------------------------------------------------------------
# Low-level transforms
# ---------------------------------------------------------------------------


def _strip(v: Any) -> Any:
    return v.strip() if isinstance(v, str) else v


def _norm(v: Any) -> Any:
    """Strip whitespace and lowercase."""
    return v.strip().lower() if isinstance(v, str) else v


# ---------------------------------------------------------------------------
# Annotated field types
# ---------------------------------------------------------------------------

TrimStr = Annotated[str, BeforeValidator(_strip)]
NormStr = Annotated[str, BeforeValidator(_norm)]  # strip + lowercase


# ---------------------------------------------------------------------------
# Base model
# ---------------------------------------------------------------------------


class NormModel(BaseModel):
    """
    Pydantic base model that strips leading/trailing whitespace from every
    string field before validation.  Individual fields that also need
    lowercasing should use the NormStr annotated type.
    """

    @model_validator(mode="before")
    @classmethod
    def _strip_all_strings(cls, values: Any) -> Any:
        if isinstance(values, dict):
            return {k: _strip(v) for k, v in values.items()}
        return values


# ---------------------------------------------------------------------------
# Query-parameter helpers
# ---------------------------------------------------------------------------


def strip_param(v: Optional[str]) -> Optional[str]:
    """Strip whitespace from an optional query parameter."""
    return v.strip() if isinstance(v, str) else v


def norm_param(v: Optional[str]) -> Optional[str]:
    """Strip and lowercase an optional query parameter."""
    return v.strip().lower() if isinstance(v, str) else v


# ---------------------------------------------------------------------------
# Redirect-target validation
# ---------------------------------------------------------------------------


def validate_relative_redirect(target: str | None) -> str | None:
    """Return *target* as a same-origin relative path, or None if hostile.

    Used by endpoints that accept a caller-supplied path
    (``?redirect_to=`` / ``?return_to=``). Browsers normalize ``\\`` to ``/``
    per WHATWG URL parsing, so ``/\\evil.com`` would be interpreted as
    protocol-relative ``//evil.com`` — the guard normalizes first, then
    rejects anything carrying a scheme, host, or leading ``//``.

    Also rejects ASCII control characters (CR, LF, tab, NUL) as defense in
    depth against Location-header smuggling if downstream URL quoting ever
    regresses, and to keep audit logs of rejected values injection-safe.

    Accepts ``None`` and empty strings (returns None for both) so callers
    can pass query-param values directly without pre-filtering. Returns the
    backslash-normalized safe path on success. Callers should fall back to a
    known-safe default and audit-log the rejection.
    """
    if not target:
        return None
    if any(c in target for c in "\r\n\t\x00"):
        return None
    candidate = target.replace("\\", "/")
    if not candidate.startswith("/") or candidate.startswith("//"):
        return None
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc:
        return None
    return candidate
