"""Canonical API identity models shared across layers."""

from pydantic import BaseModel


class APIReference(BaseModel):
    """Identifies a target API — the strict (all-required) variant.

    Used in responses and as the canonical identity tuple.
    """

    vendor: str
    name: str
    version: str


class APIReferenceRequest(BaseModel):
    """Relaxed variant for request bodies where partial identification is allowed."""

    vendor: str
    name: str = ""
    version: str = ""
