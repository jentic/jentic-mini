#!/usr/bin/env bash
# Import the Petstore OpenAPI spec via the registry import flow against a
# locally-running jentic-one app (make start-fixtures + make start-app).
#
# Flow:
#   1. Log in as the bootstrap admin (admin@local / 1234) to get a JWT.
#   2. POST /apis with a Petstore source to enqueue an import job.
#   3. Poll GET /jobs/{job_id} until the job leaves the queued/running state.
#
# Usage:
#   scripts/import-petstore.sh                 # import via URL source (default)
#   IMPORT_MODE=inline scripts/import-petstore.sh   # import via inline content
#
# Env overrides:
#   BASE_URL          default http://127.0.0.1:8000
#   ADMIN_EMAIL       default admin@local
#   ADMIN_PASSWORD    default 1234 (the bootstrap seed password)
#   ADMIN_NEW_PASSWORD default admin-local-12345 (used only if the bootstrap
#                      admin still has must_change_password=true; the admin
#                      surface forces a rotation before /jobs is accessible,
#                      and the new password must be >= 12 chars)
#   PETSTORE_URL      default https://petstore3.swagger.io/api/v3/openapi.json
#   IMPORT_MODE       url (default) | inline
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-1234}"
ADMIN_NEW_PASSWORD="${ADMIN_NEW_PASSWORD:-admin-local-12345}"
PETSTORE_URL="${PETSTORE_URL:-https://petstore3.swagger.io/api/v3/openapi.json}"
IMPORT_MODE="${IMPORT_MODE:-url}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "error: '$1' is required" >&2; exit 1; }; }
need curl
need jq

login() {
  # echo the access token for the given password, or empty on failure
  curl -sS -X POST "${BASE_URL}/auth/login" \
    -H 'Content-Type: application/json' \
    -d "$(jq -n --arg e "$ADMIN_EMAIL" --arg p "$1" '{email: $e, password: $p}')" \
    | jq -r '.access_token // empty'
}

echo "==> Logging in as ${ADMIN_EMAIL} at ${BASE_URL}/auth/login"
LOGIN_RESP="$(curl -sS -X POST "${BASE_URL}/auth/login" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg e "$ADMIN_EMAIL" --arg p "$ADMIN_PASSWORD" \
        '{email: $e, password: $p}')")"

TOKEN="$(echo "$LOGIN_RESP" | jq -r '.access_token // empty')"
MUST_CHANGE="$(echo "$LOGIN_RESP" | jq -r '.must_change_password // false')"

# Fall back to the rotated password if the seed password was already changed.
if [[ -z "$TOKEN" ]]; then
  TOKEN="$(login "$ADMIN_NEW_PASSWORD")"
  MUST_CHANGE=false
fi

if [[ -z "$TOKEN" ]]; then
  echo "error: failed to obtain access token (tried ADMIN_PASSWORD and ADMIN_NEW_PASSWORD)" >&2
  echo "$LOGIN_RESP" >&2
  exit 1
fi
echo "    got access token (must_change_password=${MUST_CHANGE})"

# The admin surface blocks protected resources (e.g. /jobs) until the bootstrap
# admin rotates its password, so do it once transparently.
if [[ "$MUST_CHANGE" == "true" ]]; then
  echo "==> Rotating bootstrap admin password (required before /jobs access)"
  curl -sS -f -X POST "${BASE_URL}/users/me:change-password" \
    -H "Authorization: Bearer ${TOKEN}" -H 'Content-Type: application/json' \
    -d "$(jq -n --arg c "$ADMIN_PASSWORD" --arg n "$ADMIN_NEW_PASSWORD" \
          '{current_password: $c, new_password: $n}')"
  TOKEN="$(login "$ADMIN_NEW_PASSWORD")"
  if [[ -z "$TOKEN" ]]; then
    echo "error: re-login after password rotation failed" >&2
    exit 1
  fi
  echo "    rotated and re-authenticated"
fi

echo "==> Building import request (mode=${IMPORT_MODE})"
if [[ "$IMPORT_MODE" == "inline" ]]; then
  SPEC_CONTENT="$(curl -sS -f "$PETSTORE_URL")"
  IMPORT_BODY="$(jq -n --arg c "$SPEC_CONTENT" '
    {sources: [{
      type: "inline",
      content: $c,
      filename: "petstore.json",
      vendor: "swagger.io",
      api_name: "petstore",
      submitted_by: "import-petstore.sh"
    }]}')"
else
  IMPORT_BODY="$(jq -n --arg u "$PETSTORE_URL" '
    {sources: [{
      type: "url",
      url: $u,
      vendor: "swagger.io",
      api_name: "petstore",
      submitted_by: "import-petstore.sh"
    }]}')"
fi

echo "==> POST ${BASE_URL}/apis"
IMPORT_RESP="$(curl -sS -f -X POST "${BASE_URL}/apis" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d "$IMPORT_BODY")"

echo "$IMPORT_RESP" | jq .
JOB_ID="$(echo "$IMPORT_RESP" | jq -r '.job_id')"
if [[ -z "$JOB_ID" || "$JOB_ID" == "null" ]]; then
  echo "error: no job_id in response" >&2
  exit 1
fi

echo "==> Polling job ${JOB_ID}"
for _ in $(seq 1 30); do
  JOB_RESP="$(curl -sS -f "${BASE_URL}/jobs/${JOB_ID}" \
    -H "Authorization: Bearer ${TOKEN}")"
  STATUS="$(echo "$JOB_RESP" | jq -r '.status // .state // "unknown"')"
  echo "    status=${STATUS}"
  case "$STATUS" in
    queued|running|in_progress|pending) sleep 1 ;;
    *) echo "$JOB_RESP" | jq .; break ;;
  esac
done

echo "==> Done"
