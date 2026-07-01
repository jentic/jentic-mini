"""Unit tests for the broker response header assembly (§04 tracestate echo)."""

from __future__ import annotations

from jentic_one.broker.core.headers import TRACESTATE_HEADER
from jentic_one.broker.core.schemas import ExecuteRequestContext
from jentic_one.broker.web.routers.execute import _metadata_headers


def _ctx(**overrides: object) -> ExecuteRequestContext:
    base: dict[str, object] = {
        "upstream_url": "https://api.stripe.com/v1/charges",
        "method": "POST",
        "trace_id": "trace-1",
        "toolkit_id": "tk_abc123",
        "operation_id": "op_1",
        "api_vendor": "stripe",
        "api_name": "payments",
        "api_version": "2023-10-16",
    }
    base.update(overrides)
    return ExecuteRequestContext(**base)  # type: ignore[arg-type]


def test_metadata_headers_echo_jentic_tracestate():
    """The response carries the packed jentic= tracestate member."""
    headers = _metadata_headers(_ctx(), "exec_xyz789")
    assert headers[TRACESTATE_HEADER] == "jentic=exec_xyz789:tk_abc123:stripe:payments:2023-10-16"


def test_metadata_headers_tracestate_uses_placeholders_for_missing_fields():
    """Missing toolkit/api segments still produce a fixed five-field member."""
    headers = _metadata_headers(
        _ctx(toolkit_id=None, api_vendor=None, api_name=None, api_version=None),
        "exec_1",
    )
    assert headers[TRACESTATE_HEADER] == "jentic=exec_1:_:_:_:_"
