"""Contract test: the broker ``_PIN`` regex matches the OpenAPI spec (§10).

The ``_PIN`` constant in ``broker/core/revisions.py`` validates every
``Jentic-Revision`` value at the edge. It must stay byte-for-byte in sync with
the ``pattern`` declared on the ``JenticRevision`` parameter in the hand-curated
``openapi/broker/broker.openapi.yaml`` — otherwise the broker could reject (or
accept) values the published contract disagrees with. This drift guard fails
loudly the moment the two diverge.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from jentic_one.broker.core.revisions import _PIN

OPENAPI_DIR = Path(__file__).resolve().parent.parent.parent / "openapi"
BROKER_SPEC_PATH = OPENAPI_DIR / "broker" / "broker.openapi.yaml"

_PARAMETER_NAME = "JenticRevision"


@pytest.mark.arch
def test_pin_regex_matches_spec_pattern() -> None:
    spec = yaml.safe_load(BROKER_SPEC_PATH.read_text(encoding="utf-8"))
    parameters = spec["components"]["parameters"]
    assert _PARAMETER_NAME in parameters, (
        f"{_PARAMETER_NAME} parameter missing from broker.openapi.yaml"
    )

    param = parameters[_PARAMETER_NAME]
    assert param["name"] == "Jentic-Revision"
    spec_pattern = param["schema"]["items"]["pattern"]

    assert _PIN.pattern == spec_pattern, (
        "broker _PIN regex drifted from the JenticRevision spec pattern: "
        f"{_PIN.pattern!r} != {spec_pattern!r}"
    )
