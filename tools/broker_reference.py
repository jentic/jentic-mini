"""Offline exporter for the hand-curated Broker OpenAPI spec.

The Broker is the platform's **data plane** — a standalone service that runs as
the sole surface (``__main__`` refuses to bundle it with the control plane), so
its spec is never part of the combined control-plane ``/openapi.json``. Its
public contract is maintained by hand at ``openapi/broker/broker.openapi.yaml``.

The docs SPA renders the Broker as its own API-reference section, fetching a
committed JSON artifact (``ui/public/broker-openapi.json``) the same way it
fetches the generated CLI reference. This tool converts the canonical YAML to
that JSON artifact deterministically so the two never drift.

Run directly::

    uv run python -m tools.broker_reference            # writes the JSON artifact
    uv run python -m tools.broker_reference --stdout    # print to stdout
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
BROKER_SPEC_YAML = REPO_ROOT / "openapi" / "broker" / "broker.openapi.yaml"
BROKER_SPEC_JSON = REPO_ROOT / "ui" / "public" / "broker-openapi.json"


def load_broker_spec() -> dict[str, Any]:
    """Parse the canonical hand-curated broker spec from YAML."""
    raw = BROKER_SPEC_YAML.read_text(encoding="utf-8")
    spec = yaml.safe_load(raw)
    if not isinstance(spec, dict):
        raise ValueError(f"{BROKER_SPEC_YAML} did not parse to a mapping")
    return spec


def dump_spec_json(spec: dict[str, Any]) -> str:
    """Serialise the broker spec to deterministic, sorted JSON."""
    return json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_broker_spec(path: Path | None = None) -> Path:
    """Generate the broker JSON artifact and write it to ``path``."""
    target = path or BROKER_SPEC_JSON
    spec = load_broker_spec()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dump_spec_json(spec), encoding="utf-8")
    return target


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the generated JSON to stdout instead of writing the file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the JSON to this path (defaults to ui/public/broker-openapi.json).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.stdout:
        sys.stdout.write(dump_spec_json(load_broker_spec()))
        return 0
    output = args.output.resolve() if args.output is not None else None
    written = write_broker_spec(output)
    try:
        display = written.relative_to(REPO_ROOT)
    except ValueError:
        display = written
    sys.stderr.write(f"Wrote {display}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
