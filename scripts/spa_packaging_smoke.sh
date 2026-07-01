#!/usr/bin/env bash
# Packaging smoke: build the real UI + wheel, install into a throwaway venv,
# and assert the bundled SPA is packaged and served correctly (DB-free).
#
# This is the only check that exercises the UI↔backend packaging seam against a
# *real* installed wheel — local unit tests use a fake static dir. It needs no
# Postgres because SPA static serving is independent of the database.
#
# Usage: scripts/spa_packaging_smoke.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV_DIR="$(mktemp -d)/spa-smoke"
trap 'rm -rf "$(dirname "$VENV_DIR")"' EXIT

echo "==> Building UI bundle"
(cd ui && npm ci && npm run build)

echo "==> Building wheel (with bundled UI)"
rm -f dist/*.whl
uv build --wheel

echo "==> Installing wheel into a clean venv (constrained to the lockfile)"
# Export the locked runtime deps so the smoke tests the versions we actually
# ship, not whatever the resolver picks as "latest". Without this the venv can
# pull a newer FastAPI/Starlette than uv.lock pins and diverge from production.
uv export --frozen --no-dev --no-emit-project -o "$VENV_DIR.constraints.txt"
uv venv "$VENV_DIR"
uv pip install --python "$VENV_DIR/bin/python" -c "$VENV_DIR.constraints.txt" dist/*.whl

echo "==> Running DB-free packaging smoke"
"$VENV_DIR/bin/python" scripts/spa_packaging_smoke.py
