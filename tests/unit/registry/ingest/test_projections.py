"""Unit tests for operation projection strategies."""

from __future__ import annotations

from jentic_one.registry.core.schema.operations import Operation
from jentic_one.registry.ingest.embeddings.projections.weighted_simple import (
    WeightedSimpleProjection,
)


def _op(
    *,
    path: str,
    method: str,
    operation_id: str | None = None,
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> Operation:
    return Operation(
        id="op_test",
        operation_id=operation_id,
        path=path,
        method=method,
        summary=summary,
        description=description,
        tags=tags,
    )


def test_weighted_simple_emits_weighted_markers():
    proj = WeightedSimpleProjection()
    op = _op(
        path="/users/{id}",
        method="get",
        operation_id="getUser",
        summary="Get a user",
        tags=["users"],
    )
    text = proj.create_projection(op, "acme", "user-api")

    # operation_id is the primary identifier (8x) with markers
    assert text.count("OPERATION_ID: getUser") == 8
    assert "OPERATION_CONTEXT:" in text
    # API marker bookends the text (2x leading + 1x trailing)
    assert text.count("API: user-api") >= 3
    assert "OPERATION: GET /users/{id}" in text
    assert "Tags: users" in text


def test_weighted_simple_without_operation_id_extracts_path_segments():
    proj = WeightedSimpleProjection()
    op = _op(path="/orders/items", method="post", summary="Create order item")
    text = proj.create_projection(op, "acme", "")

    # Falls back to vendor when api_name is empty
    assert "API: acme" in text
    # method+path weighted 7x when no operation_id
    assert text.count("OPERATION: POST /orders/items") == 7
    # path segments surfaced
    assert "orders" in text
    assert "items" in text
