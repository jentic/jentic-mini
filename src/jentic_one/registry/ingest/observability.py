"""Ingest telemetry — tracer and metric instruments for the ingest pipeline."""

from __future__ import annotations

from opentelemetry import trace

from jentic_one.shared.metrics import get_meter

tracer = trace.get_tracer("registry.ingest")

_meter = get_meter("registry.ingest")

ingests_total = _meter.create_counter("ingest.total", description="Total ingest attempts")
ingest_duration = _meter.create_histogram(
    "ingest.duration_ms", unit="ms", description="Ingest duration in milliseconds"
)
ingest_operations = _meter.create_histogram(
    "ingest.operation_count", description="Number of operations extracted per ingest"
)
stages_total = _meter.create_counter("ingest.stage.total", description="Total stage executions")
stage_duration = _meter.create_histogram(
    "ingest.stage.duration_ms", unit="ms", description="Stage duration in milliseconds"
)
search_text_size = _meter.create_histogram(
    "ingest.search_text.size_chars",
    description="Total operation search-text size written to the lexical index",
)
spec_path_count = _meter.create_histogram(
    "ingest.spec.path_count", description="Number of paths in an OpenAPI spec"
)
