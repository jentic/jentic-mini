#!/bin/sh
# docker-entrypoint.sh — Jentic Mini container startup
# Runs as non-root (jentic user). All steps are idempotent.
set -e

export PYTHONPATH=/app

echo "[entrypoint] Initialising database schema..."
python3 -c "import asyncio; from src.db import init_db; asyncio.run(init_db())"

echo "[entrypoint] Seeding broker app mappings..."
python3 -c "import asyncio; from src.startup import seed_broker_apps; asyncio.run(seed_broker_apps())"

echo "[entrypoint] Starting server..."
exec uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8900 \
    --reload \
    --reload-dir /app/src \
    --reload-include "*.py"
