#!/usr/bin/env bash
set -euo pipefail

# Docker E2E test lifecycle script
# Builds, starts, health-checks, runs Playwright, then tears down.

COMPOSE="docker compose -f compose.yml -f compose.ci.yml"
MAX_WAIT=60
SCRIPT_EXIT_CODE=0

cleanup() {
  if [[ "$SCRIPT_EXIT_CODE" -ne 0 || "${DEBUG_DOCKER_E2E:-}" != "" ]]; then
    echo "--- Dumping container logs (exit code: ${SCRIPT_EXIT_CODE}) ---"
    $COMPOSE logs --no-color 2>/dev/null || true
  fi
  echo "--- Tearing down ---"
  $COMPOSE down -v 2>/dev/null || true
}
trap cleanup EXIT

echo "==> Cleaning up any previous run..."
$COMPOSE down -v 2>/dev/null || true

echo "==> Building and starting containers..."
$COMPOSE up -d --build

echo "==> Waiting for health check (max ${MAX_WAIT}s)..."
for i in $(seq 1 $MAX_WAIT); do
  if curl -sf http://localhost:8900/health > /dev/null 2>&1; then
    echo "Server is ready after ${i}s"
    break
  fi
  if [ "$i" -eq "$MAX_WAIT" ]; then
    echo "Server failed to start within ${MAX_WAIT}s"
    SCRIPT_EXIT_CODE=1
    exit 1
  fi
  sleep 1
done

echo "==> Running Docker E2E tests..."
cd ui
rm -f e2e/docker/.docker-e2e-state.json
npx playwright test --config=playwright.docker.config.ts || { SCRIPT_EXIT_CODE=$?; exit $SCRIPT_EXIT_CODE; }
echo "==> All Docker E2E tests passed"
