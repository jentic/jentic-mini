# Versioning Strategy

## What We Have Now

### Git tags + CI (standard Docker pattern)

The version is defined by the **git tag** (e.g. `v0.1.0`). CI extracts the version and passes it as a Docker build arg. No VERSION file — the tag is the single source of truth.

The `Dockerfile` declares a dev default that CI overrides:

```dockerfile
ARG APP_VERSION=0.1.0
ENV APP_VERSION=${APP_VERSION}
```

`src/config.py` reads the env var with the same dev fallback:

```python
APP_VERSION = os.getenv("APP_VERSION", "unknown")
```

CI overrides at build time from the git tag:

```bash
docker build --build-arg APP_VERSION=${GITHUB_REF_NAME#v} -t jentic-mini:latest .
```

In Docker, `APP_VERSION` is always set by the Dockerfile ARG/ENV. The `config.py` fallback (`"unknown"`) only applies to bare-metal dev where the env var is unset — it signals that the version hasn't been injected. Semantic-release bumps the Dockerfile default automatically on each release.

The version is exposed in:
- `GET /health` — `version` field
- `GET /version` — `current` field (frontend reads this for update checks)
- OCI image label `org.opencontainers.image.version`
- The FastAPI OpenAPI schema (`/docs`)

---

## Update Check Mechanism

### How it works

1. The **backend** (`GET /version`) calls the GitHub releases API and caches the result for **6 hours**. This avoids every browser tab hitting GitHub directly (rate limit: 60 req/hr per IP for unauthenticated requests).

2. The **frontend** (`useUpdateCheck` hook) calls `/version` on page load, compares the latest GitHub release tag against the current version using semver, and shows an amber "Update available: vX.Y.Z" badge in the sidebar footer if a newer version exists.

3. The result is cached in `sessionStorage` so it only runs once per browser session.

4. The `v` prefix is stripped before comparison — `v0.1.1` and `0.1.1` are treated identically.

### Opting out

Set `JENTIC_TELEMETRY=off` to disable the outbound GitHub check entirely. The `/version` endpoint will still return the current version but `latest` and `release_url` will be `null`, so no update badge will appear.

```bash
docker run -d --name jentic-mini -p 8900:8900 \
  -v jentic-mini-data:/app/data \
  -e JENTIC_TELEMETRY=off \
  jentic/jentic-mini
```

---

## What's Still To Do

### 1. GitHub release process (priority: low, pre-release)

Currently releases are published manually via the GitHub UI. For a proper release cadence:

- Use [Release Please](https://github.com/googleapis/release-please) or similar to automate changelog + tag creation from conventional commits
- Or keep it manual but document the checklist

### 4. Version pinning for Docker Compose users (priority: low)

Self-hosters using `docker compose` should be able to pin to a specific version. Once images are published to a registry (GHCR or Docker Hub), the compose file should reference a versioned tag rather than `latest`:

```yaml
image: ghcr.io/jentic/jentic-mini:0.1.0  # pin to a release
# or
image: ghcr.io/jentic/jentic-mini:latest  # always latest
```

This isn't relevant until images are published to a registry.

### 5. Backend-initiated update notifications (future)

Currently the update check is purely client-side. A future option is for the backend to log a warning on startup if it detects it's running an outdated version — useful for headless/API-only deployments where no one opens the UI.

---

## Decision Log

| Decision | Rationale |
|---|---|
| Git tag as version source of truth | Standard Docker pattern (Traefik, Prometheus, Grafana); CI passes `--build-arg` |
| `APP_VERSION` env var + dev fallback | Dockerfile ARG/ENV sets it in Docker; `config.py` fallback for bare-metal dev; both must match |
| Frontend reads `current` from `/version` | No hardcoded version in the client; always reflects what the backend actually reports |
| Backend proxies GitHub API check | Avoids browser rate limits (60 req/hr unauthenticated per IP); works for private repos; allows server-side caching |
| 6-hour cache TTL | ~4 GitHub API calls/day per deployment; well within unauthenticated limits even with many installs |
| `sessionStorage` cache in browser | Avoids re-checking on every page navigation within a session; clears on tab close |
| Strip `v` prefix in semver comparison | GitHub tags conventionally use `v0.1.0`; backend version strings conventionally don't |
