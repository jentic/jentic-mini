"""Unit tests for the projection factory."""

from __future__ import annotations

from jentic_one.registry.ingest.embeddings.projections import get_projection
from jentic_one.registry.ingest.embeddings.projections.weighted_simple import (
    WeightedSimpleProjection,
)


def test_get_projection_returns_weighted_simple() -> None:
    assert isinstance(get_projection(), WeightedSimpleProjection)
