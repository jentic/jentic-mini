# Versioning Strategy

## What We Have Now

### Single source of truth: `APP_VERSION`

The version number lives in one place — the `Dockerfile`:

```dockerfile
ARG APP_VERSION=0.1.0
ENV APP_VERSION=${APP_VERSION}
```

The Python backend reads it at runtime:

```python
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
```

The fallback in `main.py` should always match the Dockerfile default. CI can override at build time:

```bash
docker build --build-arg APP_VERSION=0.2.0 -t jentic-mini:latest .
```

The version is exposed in:
- `GET /health` — `version` field
- `GET /version` — `current` field
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

### Current limitation (temporary)

The client-side baseline version is **hardcoded as `"0.1.0"`** in `useUpdateCheck.ts`:

```ts
const CURRENT_VERSION = '0.1.0'
```

This means every installation currently reports itself as `0.1.0` regardless of what version is actually running. The badge will fire correctly for any GitHub release > `0.1.0`, but it won't distinguish between installations running different versions.

---

## What's Still To Do

### 1. Wire up dynamic current version in the frontend (priority: medium)

Replace the hardcoded `"0.1.0"` in `useUpdateCheck.ts` with the value from `GET /version`:

```ts
const currentVersion: string = data.current  // from backend
```

This is already returned by the `/version` endpoint — the hook just needs to use it. Blocked on the backend version being reliably set at build time (see item 2).

### 2. Automate version bumping in CI (priority: medium)

Currently the version number must be manually updated in the Dockerfile before each release. The workflow should be:

1. Decide on the new version (e.g. `0.2.0`)
2. Update `Dockerfile` ARG (and `main.py` fallback for dev)
3. Commit, tag (`git tag v0.2.0`), push
4. CI builds the image with `--build-arg APP_VERSION=0.2.0`
5. CI publishes a GitHub release for the tag

Until CI is set up, this is a manual checklist.

### 3. GitHub release process (priority: low, pre-release)

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
| `APP_VERSION` env var as source of truth | Single place to change; CI can inject at build time; no pyproject.toml or package.json needed |
| Backend proxies GitHub API check | Avoids browser rate limits (60 req/hr unauthenticated per IP); works for private repos; allows server-side caching |
| 6-hour cache TTL | ~4 GitHub API calls/day per deployment; well within unauthenticated limits even with many installs |
| `sessionStorage` cache in browser | Avoids re-checking on every page navigation within a session; clears on tab close |
| Hardcode `0.1.0` as client baseline (temporary) | Unblocks the feature while proper version injection is set up; to be replaced within days |
| Strip `v` prefix in semver comparison | GitHub tags conventionally use `v0.1.0`; backend version strings conventionally don't |
