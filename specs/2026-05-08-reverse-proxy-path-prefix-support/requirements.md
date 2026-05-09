# Phase 25 Requirements — Reverse-Proxy Path Prefix Support

## Scope

Jentic Mini today assumes it owns its own subdomain root. Operators behind reverse proxies that serve multiple apps under a shared host (Caddy `handle_path /jentic/*`, Traefik `PathPrefix(/foo)`, nginx Ingress `path: /foo`) must dedicate a subdomain to the instance — they cannot mount it at `example.com/jentic`. Phase 25 closes that gap by making both the FastAPI backend and the React SPA bundle aware of an externally configured path prefix, so the same image can serve at `/`, at `/foo` (env-pinned), or at any prefix the upstream proxy advertises via `X-Forwarded-Prefix`.

The feature is opt-in: with `JENTIC_ROOT_PATH` unset and no `X-Forwarded-Prefix`, every existing endpoint, asset, and cookie path is unchanged. With either signal present, the SPA bundle's bundled assets resolve relative to the served `index.html`, the SPA router (`createBrowserRouter`) honours the prefix as `basename`, the hand-rolled `/docs` and `/redoc` HTML reaches its vendored static assets under the prefix, and self-links emitted via `build_absolute_url` include the prefix so OAuth-broker connect callbacks and the `/health` self-link resolve correctly under the mount.

## Out of Scope

- **Real reverse-proxy round-trip in CI.** Mode C is exercised by sending `X-Forwarded-Prefix` directly to uvicorn; standing up nginx/Caddy in CI would test the proxy, not Mini.
- **Multi-mount.** FastAPI's `root_path` is a single string at app construction; serving the same instance at `/foo` and `/bar` simultaneously is not supported and is not a real-world demand.
- **WebSocket / streaming endpoints under prefix.** No WebSocket code exists in the repo; broker streaming is Phase 23's concern.
- **Pipedream OAuth callback URL configuration.** The redirect URL is configured per-broker in the Pipedream dashboard (operator action). The phase verifies the route still matches under prefix, not that Pipedream is reconfigured.
- **`JENTIC_PUBLIC_BASE_URL` auto-derivation from `JENTIC_ROOT_PATH`.** Operators must set both explicitly when mounting; the OAuth-issuer pin is security-critical and a separate phase.
- **Production-style install walkthrough.** "Production install practices" remains in Later Phases (`specs/roadmap.md`); this phase adds the env var to README + `.env.example` + compose, plus an optional Caddy snippet in `docs/deploy/digitalocean/README.md`.
- **Content-Security-Policy adjustments.** No CSP is currently emitted; introducing one is its own phase.
- **`docs/reverse-proxy.md` as a new file.** README + env-var entry is enough for this phase.

## Decisions

### Env var name `JENTIC_ROOT_PATH`

Fits the existing `JENTIC_*` naming convention (`JENTIC_VAULT_KEY`, `JENTIC_PUBLIC_HOSTNAME`, `JENTIC_PUBLIC_BASE_URL`, `JENTIC_TRUSTED_SUBNETS`, `JENTIC_INTERNAL_PORT`, etc.). No collision with any existing variable. Already used in issue #356 verbatim — locking it in here.

### Header name `X-Forwarded-Prefix`

The de-facto standard used by Traefik and nginx Ingress; not in any RFC. `X-Script-Name` (Werkzeug/Flask) and `X-Original-URI` (nginx-specific) would surprise the most common Mini deploy targets. Locking `X-Forwarded-Prefix`.

### Precedence: `JENTIC_ROOT_PATH` env wins over header

If `JENTIC_ROOT_PATH` is set, it is the source of truth and `X-Forwarded-Prefix` is ignored. If unset, the header is read per-request via ASGI middleware that mutates `scope["root_path"]`. Env-pinned config wins over per-request headers, mirroring the `JENTIC_PUBLIC_BASE_URL` pattern (operator-pinned canonical URL preferred over `X-Forwarded-Host` for security-sensitive surfaces).

### Prefix normalisation and validation

Empty string, unset, and bare `/` all mean "no mount". A non-empty prefix is normalised by stripping the trailing slash (`/foo/` → `/foo`). Invalid shapes — value not starting with `/`, containing whitespace, fragments, queries, or `..` — fail fast at startup with a `RuntimeError` carrying a helpful message, mirroring the existing `config.py` validation pattern (e.g. the `AGENT_NONCE_WINDOW <= AGENT_ASSERTION_MAX_AGE` check).

### `<base href>` value includes a trailing slash

Per HTML §4.2.3, browsers resolve relative URLs against `<base href>` differently depending on the trailing slash: `<base href="/foo">` resolves `assets/x.js` to `/assets/x.js` (sibling), while `<base href="/foo/">` resolves to `/foo/assets/x.js`. The injected value is `{root_path}/` with the trailing slash intentionally preserved.

### React Router `basename` from `document.baseURI`

`createBrowserRouter` does not read `<base href>` at all (verified — `react-router-dom@^6.30.3`). It needs `basename` passed explicitly. The standard Vite pattern `basename: import.meta.env.BASE_URL` would tie the SPA bundle to one prefix at build time, defeating the goal of "any prefix from the same image". Reading `<base href>` from the DOM at app load — `new URL(document.baseURI).pathname.replace(/\/$/, '') || undefined` — uses the dynamic value the backend just injected and keeps the bundle prefix-agnostic.

### `OpenAPI.BASE` derived from `document.baseURI`

The generated UI client ships with `OpenAPI.BASE = ''` (`ui/src/main.tsx:10`), assuming same-origin relative URLs. Under prefix mounting, naïvely-resolved absolute paths like `/credentials` skip the `<base>` and hit origin root. Setting `OpenAPI.BASE = new URL(document.baseURI).pathname.replace(/\/$/, '')` (path component only, not the full URL) keeps the client prefix-aware without bundling the prefix at build time and preserves the existing same-origin assumption (the generated client at `ui/src/api/generated/core/request.ts:96` builds URLs as `${config.BASE}${path}` with host-relative `path`s, so `BASE = "/foo"` yields `/foo/credentials`, not `https://host/foo/credentials`).

### `build_absolute_url` prepends `request.scope["root_path"]`

Self-links emitted by `/health` (`src/main.py:306`), the OAuth-broker connect-callback redirect URI builder (`src/routers/oauth_brokers.py:592, 1163`), and OAuth metadata routes all use `build_absolute_url(request, path)`. The current implementation builds `{scheme}://{host}{path}` with no awareness of `root_path`. Phase 25 changes this to prepend `request.scope.get("root_path", "")` to the path — without it, the OAuth-broker connect flow redirects to a 404 under any non-empty mount. This is in scope per the user's "full scope" answer.

### Auth cookies are scoped to the mount path

JWT session cookies are issued at `src/auth.py:315` and `src/routers/user.py:112,209,214` (and cleared at `src/routers/user.py:300`) without a `path` argument; Starlette's `set_cookie` defaults `path="/"`, which makes the cookie valid for the entire origin. Under shared-tenant mounts (`example.com/jentic` alongside `example.com/other-app`) the cookie leaks to siblings — a real exfiltration vector for the audience this phase serves. Phase 25 sets `path=request.scope.get("root_path") or "/"` on every cookie issuance and deletion. Reading from per-request `scope["root_path"]` (rather than the static `JENTIC_ROOT_PATH`) keeps Mode C correct, where the prefix arrives via `X-Forwarded-Prefix`.

### Operator must set both `JENTIC_ROOT_PATH` and `JENTIC_PUBLIC_BASE_URL` when mounting

`JENTIC_PUBLIC_BASE_URL` pins the OAuth issuer / `aud` / `registration_client_uri` for the Agent Identity stack and is intentionally trusted only when explicitly configured (`docs/agent-identity.md`). The phase MUST NOT auto-concatenate `root_path` into `JENTIC_PUBLIC_BASE_URL`'s output; that crosses into a security-critical mechanism whose threat model is out of scope here. Instead, the env-var documentation states: when mounting at `/foo`, set `JENTIC_PUBLIC_BASE_URL=https://example.com/foo` (including the prefix). Both env vars are documented together so operators don't miss the dependency.

### Trust `X-Forwarded-Prefix` unconditionally

Consistent with the existing precedent in `src/utils.py:8-26` (`X-Forwarded-Host`, `X-Forwarded-Proto`) and `src/auth.py:123-129` (`X-Forwarded-For`) — Mini already trusts `X-Forwarded-*` headers without an allowlist. Operators on internet-facing or shared-tenant deploys should pin `JENTIC_ROOT_PATH` explicitly, mirroring the same recommendation for `JENTIC_PUBLIC_BASE_URL`. A `JENTIC_TRUSTED_PROXIES` allowlist mechanism is its own phase.

## Constraints

- **Broker catch-all router order** (`specs/mission.md`, `specs/tech-stack.md`, `.claude/CLAUDE.md`). The broker is registered last in `src/main.py`; the new ASGI prefix middleware is registered at app construction (alongside `APIKeyMiddleware` and `negotiate_middleware`), so it does not move the broker. Verified in plan.
- **Two-actor authentication** (`specs/mission.md`). JWT cookies must be scoped to the mount path. Starlette's `set_cookie` defaults `path="/"`, so without an explicit fix a `/foo`-mounted instance issues cookies valid for the whole origin — under shared-tenant deploys (`example.com/jentic` next to `example.com/other-app`) the session cookie leaks to siblings and a malicious neighbour can exfiltrate it. Plan task 8 closes the gap by passing `path=request.scope.get("root_path") or "/"` to every `set_cookie` and `delete_cookie` call. Reading `path` from per-request `scope["root_path"]` (rather than the static `JENTIC_ROOT_PATH` config) keeps Mode C correct: the `X-Forwarded-Prefix`-driven prefix is already on the scope by the time the route handler issues the cookie. `X-Jentic-API-Key` is unaffected.
- **Capability / Workflow ID format** (`specs/mission.md`, `specs/tech-stack.md`). Workflow IDs use `JENTIC_PUBLIC_HOSTNAME`, not the path prefix. The format `POST/{JENTIC_PUBLIC_HOSTNAME}/workflows/{slug}` stays exactly the same. `root_path` is orthogonal to the capability-ID space.
- **Content-negotiation middleware** (`src/negotiate.py`). Reads `Accept` only; does not touch URLs. Orthogonal to `root_path`. Phase verifies content-type decisions on `/`, `/openapi.json`, `/docs` are unchanged.
- **Path-based middleware checks under prefix.** Multiple middlewares compare `request.url.path` against unprefixed constants: `_SPA_PATHS` in `spa_middleware` (`src/main.py`'s `/credentials`, `/toolkits`, etc.) and `_is_public` in `APIKeyMiddleware` (`src/auth.py:327-343`'s `/openapi.json`, `/docs`, `/user/login`, etc.). Starlette does NOT strip `root_path` from `scope["path"]` automatically — the strip happens only inside Starlette's routing helper `get_route_path()` for matching `@app.get(...)` decorator routes, not for arbitrary middleware reads. Without intervention, `/foo/openapi.json` would be treated as authenticated and `/foo/credentials` cold-boots would 404. Plan task 6 closes this once for all consumers by stripping `root_path` from `scope["path"]` inside the new ASGI middleware (matching the standard ASGI behind-a-proxy pattern); every downstream middleware sees the unprefixed form and works without per-consumer modifications.
- **`JENTIC_PUBLIC_BASE_URL` security pin** (`docs/agent-identity.md`). The phase does NOT extend or mutate this mechanism; it documents the relationship and leaves the OAuth-issuer pin as operator-configured.

## Context

Mini has shipped two of the three pieces required for path-prefix mounting: `JENTIC_PUBLIC_BASE_URL` (introduced with the Agent Identity work, referenced in `docs/agent-identity.md`) anchors the OAuth-discoverable URLs, and `build_absolute_url` (`src/utils.py`) honours `X-Forwarded-Host` for self-links. What's missing is the prefix awareness in (a) FastAPI's routing, (b) the SPA bundle's asset URLs and React Router, and (c) the hand-rolled `/docs`/`/redoc` HTML. Phase 25 wires all three.

The change pairs naturally with `docs/deploy/digitalocean/README.md` — the only deploy recipe shipped today shows a Caddy `reverse_proxy localhost:8900` at the subdomain root, and a `handle_path /jentic/* { reverse_proxy ... }` variant becomes available once this phase ships. The phase does not block on producing that variant — it can land as a follow-up patch — but the env-var entry in `README.md` and `.env.example` is in scope.

The deeper trajectory is reverse-proxy compatibility for a self-hosted-first product: more deploy patterns means more agents wired up. `specs/mission.md` lists self-hosters and open-source ecosystem adopters as first-class audiences; path-prefix mounting unblocks a real subset of those users today (homelab setups, shared-tenant boxes, docker-compose stacks with a single ingress).

## Stakeholder Notes

- **Self-hosters** — primary beneficiaries. Many run a single-machine box behind one ingress proxy (Caddy/Traefik/nginx) with several services on shared subdomains; today they must dedicate a subdomain to Mini. Phase 25 lets them mount at a path.
- **Open-source ecosystem adopters** — homelab and unraid-style deployments where path-based routing is the common pattern. Same need.
- **Small teams** — benefit when deploying alongside other services under shared TLS.
- **Agent frameworks** — indirectly. They consume URLs the operator gives them; the prefix is absorbed by the canonical base URL the operator sets via `JENTIC_PUBLIC_BASE_URL`. Workflow capability IDs (which use `JENTIC_PUBLIC_HOSTNAME`, not `root_path`) are unchanged, so persisted IDs stay valid.
