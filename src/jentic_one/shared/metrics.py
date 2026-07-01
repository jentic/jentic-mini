"""Metrics facade — the single sanctioned entry point for application metrics.

All application code under `src/` should use `get_meter()` from this module
to create instruments. No source module outside this file may import
`prometheus_client` or any `opentelemetry.exporter.*` package directly —
this is enforced by `tests/arch/test_metrics_facade.py`. Tests under
`tests/` are exempt so they can poke at internals when needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from prometheus_client import make_asgi_app

from jentic_one.shared.config import MetricsConfig

if TYPE_CHECKING:
    from opentelemetry.metrics import Meter

_configured = False
_prometheus_active = False


def configure_metrics(service_name: str, config: MetricsConfig) -> MeterProvider | None:
    """Configure the global MeterProvider based on the chosen exporter.

    Returns the MeterProvider if one was created, or None for the "none" exporter.
    Idempotent — subsequent calls return immediately.
    """
    global _configured, _prometheus_active
    if _configured:
        current = metrics.get_meter_provider()
        if isinstance(current, MeterProvider):
            return current
        return None

    _configured = True

    if config.exporter == "none":
        return None

    resource = Resource.create({"service.name": service_name})

    reader: MetricReader
    if config.exporter == "prometheus":
        reader = PrometheusMetricReader()
        _prometheus_active = True
    else:
        otlp_exporter = OTLPMetricExporter()
        reader = PeriodicExportingMetricReader(
            otlp_exporter, export_interval_millis=config.export_interval_seconds * 1000
        )

    provider = MeterProvider(resource=resource, metric_readers=[reader])

    metrics.set_meter_provider(provider)
    return provider


def get_meter(name: str) -> Meter:
    """Return a Meter from the global MeterProvider."""
    return metrics.get_meter(name)


def make_metrics_asgi_app() -> Any | None:
    """Return a Prometheus ASGI app if the prometheus reader is active, else None."""
    if not _prometheus_active:
        return None
    return make_asgi_app()


def reset_metrics() -> None:
    """Reset metrics state — for testing only.

    Clears both this module's guard flags and OpenTelemetry's set-once
    global so a fresh `configure_metrics()` call in the next test takes
    effect. Touches OTel internals on purpose; if a future SDK release
    breaks the attribute names, fix it here in one place.
    """
    global _configured, _prometheus_active
    _configured = False
    _prometheus_active = False
    metrics._internal._METER_PROVIDER = None
    metrics._internal._METER_PROVIDER_SET_ONCE._done = False
