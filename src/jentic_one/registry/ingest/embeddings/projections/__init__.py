"""Factory for creating operation projection strategy instances."""

from __future__ import annotations

from jentic_one.registry.ingest.embeddings.projections.base import Projection
from jentic_one.registry.ingest.embeddings.projections.weighted_simple import (
    WeightedSimpleProjection,
)


def get_projection() -> Projection:
    """Build the operation text projection strategy.

    Lexical search indexes the repetition-weighted ``WeightedSimpleProjection``
    text — the only projection strategy now that the intent-based NLP pipeline
    (spaCy/corpus-stats) has been removed.
    """
    return WeightedSimpleProjection()
