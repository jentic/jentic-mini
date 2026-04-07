#!/usr/bin/env bash
# Manual upgrade script for Jentic Mini.
# Run this on the host if Watchtower is not configured.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Pulling latest Jentic Mini image..."
docker compose pull jentic-mini
echo "Restarting..."
docker compose up -d jentic-mini
echo "Jentic Mini updated successfully."
