"""
Input normalisation helpers for Jentic Mini.

NormModel  — base class: strips whitespace from every string field before validation.
NormStr    — Annotated type: strips + lowercases (use for enum-like fields: type, effect…).
TrimStr    — Annotated type: strips only (use where case matters: name, label, URL…).
strip_param / norm_param — normalise optional query-parameter strings.
"""

from typing import Annotated, Any, Optional

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
