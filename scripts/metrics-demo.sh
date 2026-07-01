#!/usr/bin/env bash
# scripts/metrics-demo.sh
#
# End-to-end "see metrics in action" walkthrough for the local kind cluster.
#
# Idempotent: re-running picks up wherever the previous run left off. Skips
# expensive steps (image build, cluster create, obs install) when they are
# already done. Use --force-rebuild to override.
#
# Usage:
#   scripts/metrics-demo.sh                       # OTLP path (default), MODE=combined
#   scripts/metrics-demo.sh --path prom           # Prometheus scrape path
#   scripts/metrics-demo.sh --mode parts          # parts mode (registry+admin+control+broker)
#   scripts/metrics-demo.sh --skip-build          # reuse existing images (default: rebuild)
#   scripts/metrics-demo.sh --traffic 100         # send 100 requests instead of the default 50
#   scripts/metrics-demo.sh --no-grafana          # skip the port-forward + browser open
#
# What it does:
#   1. Builds service images (skip with --skip-build).
#   2. Brings up the kind cluster if absent.
#   3. Installs/upgrades the observability stack (Grafana/Loki/Tempo/Prometheus + central OTel collector).
#   4. Deploys jentic-one with the chosen metrics path:
#        otlp -> OTEL=1 (sidecar -> central collector -> prometheusremotewrite)
#        prom -> METRICS=prometheus (/metrics endpoint + scrape annotations)
#   5. Generates HTTP traffic so RED metrics actually exist.
#   6. Verifies metrics are flowing and prints a Grafana query you can paste.
#   7. Opens Grafana via `make grafana` (port-forward + browser).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Defaults — keep aligned with the Makefile.
PATH_MODE="otlp"
DEPLOY_MODE="combined"
SKIP_BUILD=0
TRAFFIC_COUNT=50
OPEN_GRAFANA=1

KIND_CLUSTER="${KIND_CLUSTER:-jentic-local}"
NAMESPACE="${NAMESPACE:-jentic}"
RELEASE="${RELEASE:-jentic}"
MONITORING_NS="${MONITORING_NS:-monitoring}"
OBS_RELEASE="${OBS_RELEASE:-obs}"
IMG_PREFIX="${IMG_PREFIX:-jentic-one}"

VERSION="$(./scripts/version.sh)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --path)            PATH_MODE="$2"; shift 2 ;;
        --mode)            DEPLOY_MODE="$2"; shift 2 ;;
        --skip-build)      SKIP_BUILD=1; shift ;;
        --traffic)         TRAFFIC_COUNT="$2"; shift 2 ;;
        --no-grafana)      OPEN_GRAFANA=0; shift ;;
        -h|--help)
            sed -n '2,30p' "$0"
            exit 0
            ;;
        *)
            echo "unknown flag: $1" >&2
            exit 2
            ;;
    esac
done

if [[ "$PATH_MODE" != "otlp" && "$PATH_MODE" != "prom" ]]; then
    echo "ERROR: --path must be 'otlp' or 'prom' (got '$PATH_MODE')" >&2
    exit 2
fi
case "$DEPLOY_MODE" in combined|parts|broker) ;; *)
    echo "ERROR: --mode must be combined|parts|broker (got '$DEPLOY_MODE')" >&2
    exit 2 ;;
esac

# Per-mode service map (keep in sync with Makefile MODE_SERVICES_*).
case "$DEPLOY_MODE" in
    combined) MODE_SERVICES=(app broker) ;;
    parts)    MODE_SERVICES=(registry admin control broker) ;;
    broker)   MODE_SERVICES=(broker) ;;
esac

# Pick a representative pod label for the traffic + verify steps.
case "$DEPLOY_MODE" in
    combined|parts) PROBE_SVC="${RELEASE}-app" ;;
    broker)         PROBE_SVC="${RELEASE}-broker" ;;
esac
# In parts mode there's no `app` service, probe registry instead.
if [[ "$DEPLOY_MODE" == "parts" ]]; then
    PROBE_SVC="${RELEASE}-registry"
fi

log() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

require() {
    command -v "$1" >/dev/null 2>&1 || die "missing required tool: $1"
}
for tool in docker kind kubectl helm make; do require "$tool"; done

# 1. Build images.
#
# We always rebuild by default. Image tags come from pyproject.toml so they
# rarely change, which means a presence-check on the tag would happily skip
# a rebuild after source edits and silently deploy stale code (this bit us
# during development). Docker layer cache makes a no-op rebuild cheap, so
# the default is "always build, opt out with --skip-build for speed".
if [[ "$SKIP_BUILD" == "1" ]]; then
    log "Skipping image build (--skip-build); assuming ${IMG_PREFIX}/<svc>:${VERSION} is current"
else
    log "Building base + service images for MODE=${DEPLOY_MODE} (services: ${MODE_SERVICES[*]})"
    make build-base
    for svc in "${MODE_SERVICES[@]}"; do
        make "build-${svc}"
    done
fi

# 2. Cluster up if missing.
if ! kind get clusters 2>/dev/null | grep -qx "$KIND_CLUSTER"; then
    log "Creating kind cluster '${KIND_CLUSTER}'"
    make cluster-up
else
    log "kind cluster '${KIND_CLUSTER}' already exists"
fi

# 3. Observability stack.
if ! helm status "$OBS_RELEASE" -n "$MONITORING_NS" >/dev/null 2>&1; then
    log "Installing observability stack (release '${OBS_RELEASE}' in '${MONITORING_NS}')"
    make obs-up
else
    log "Observability release '${OBS_RELEASE}' already present"
fi

# 4. Deploy jentic-one with the chosen metrics path.
deploy_args=(MODE="$DEPLOY_MODE")
case "$PATH_MODE" in
    otlp) deploy_args+=(OTEL=1) ;;
    prom) deploy_args+=(METRICS=prometheus) ;;
esac
log "Deploying jentic-one (${deploy_args[*]})"
make deploy-local "${deploy_args[@]}"

log "Waiting for app pods to be ready"
kubectl -n "$NAMESPACE" rollout status "deployment/${PROBE_SVC}" --timeout=120s

# 5. Generate traffic so RED metrics actually exist.
log "Generating ${TRAFFIC_COUNT} requests against ${PROBE_SVC}/health"
PF_PORT=18000
kubectl -n "$NAMESPACE" port-forward "svc/${PROBE_SVC}" "${PF_PORT}:8000" >/dev/null 2>&1 &
PF_PID=$!
trap 'kill $PF_PID 2>/dev/null || true' EXIT

# Wait briefly for the port-forward to be ready.
for _ in {1..20}; do
    if curl -sf "http://localhost:${PF_PORT}/health" >/dev/null 2>&1; then break; fi
    sleep 0.25
done

ok=0; fail=0
for ((i=0; i<TRAFFIC_COUNT; i++)); do
    if curl -sf -o /dev/null "http://localhost:${PF_PORT}/health"; then
        ok=$((ok+1))
    else
        fail=$((fail+1))
    fi
done
log "Traffic done: ${ok} ok, ${fail} failed"

# 6. Path-specific verification.
case "$PATH_MODE" in
    prom)
        log "Verifying /metrics endpoint serves OpenMetrics text"
        if curl -sf "http://localhost:${PF_PORT}/metrics/" | head -5 | grep -q '^# HELP'; then
            log "  /metrics OK"
        else
            warn "  /metrics did not return expected output. Check pod logs:"
            warn "    kubectl -n ${NAMESPACE} logs deploy/${PROBE_SVC}"
        fi
        log "Verifying scrape annotations on the pod"
        if kubectl -n "$NAMESPACE" get pod -l "app.kubernetes.io/name=${PROBE_SVC#${RELEASE}-}" \
                -o jsonpath='{.items[0].metadata.annotations}' \
                | grep -q 'prometheus.io/scrape'; then
            log "  annotations OK"
        else
            warn "  scrape annotations missing. helm template the chart and inspect."
        fi
        ;;
    otlp)
        log "Verifying app pod has OTel sidecar"
        ready=$(kubectl -n "$NAMESPACE" get pod -l "app.kubernetes.io/name=${PROBE_SVC#${RELEASE}-}" \
                -o jsonpath='{.items[0].status.containerStatuses[*].ready}')
        if [[ "$ready" == "true true" ]]; then
            log "  sidecar Ready alongside app container"
        else
            warn "  pod not 2/2 Ready (containers: $ready). Check logs:"
            warn "    kubectl -n ${NAMESPACE} logs deploy/${PROBE_SVC} -c otel-collector"
        fi
        log "Tailing central OTel collector for metric activity (5s)"
        kubectl -n "$MONITORING_NS" logs "deploy/${OBS_RELEASE}-otelcollector" --tail=20 --since=10s \
            | grep -iE 'metric|otlp' \
            || warn "  no metric activity in the central collector yet (give it a minute)"
        ;;
esac

# 7. Open Grafana.
cat <<EOF

Metrics demo deployed. Useful next steps:

  Grafana → Explore → Prometheus datasource. Try:

    sum by(service_name, http_route) (rate(http_server_duration_milliseconds_count[1m]))

  Or directly in Prometheus:

    kubectl -n ${MONITORING_NS} port-forward svc/${OBS_RELEASE}-prometheus-server 9090:80
    open http://localhost:9090/targets    # ${PATH_MODE} path → look for the 'jentic-pods' job

  Tear it all down:

    make undeploy-local
    make obs-down
    make cluster-down

EOF

if [[ "$OPEN_GRAFANA" == "1" ]]; then
    # Drop the port-forward we owned; `make grafana` runs its own.
    kill $PF_PID 2>/dev/null || true
    trap - EXIT
    log "Opening Grafana (Ctrl-C to release the port-forward)"
    exec make grafana
fi
