#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('${REPO_ROOT}/pyproject.toml').read_text())['project']['version'])"
