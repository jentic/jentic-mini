#!/bin/sh
# docker-entrypoint.sh — Jentic Mini container startup
# Runs as non-root (jentic user). All steps are idempotent.
set -e

export PYTHONPATH=/app

echo "[entrypoint] Running database migrations..."
/app/.venv/bin/python -m alembic upgrade head

echo "[entrypoint] Seeding broker app mappings..."
/app/.venv/bin/python -c "import asyncio; from src.startup import seed_broker_apps; asyncio.run(seed_broker_apps())"

echo "[entrypoint] Starting server..."
exec /app/.venv/bin/uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8900 \
    --log-level "${LOG_LEVEL:-info}" \
    --reload \
    --reload-dir /app/src \
    --reload-include "*.py"
