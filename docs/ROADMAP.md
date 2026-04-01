# Roadmap

## Completed

### Core Infrastructure

- FastAPI + SQLite service on port 8900 with uvicorn hot reload
- Docker Compose deployment with multi-stage build (Node → Python, no Node in final image)
- Fernet-encrypted credential vault (write-only semantics)
- Swagger UI + Redoc served locally from vendored assets (no CDN dependency)
- React + Vite admin UI (TailwindCSS 4, CSS custom property design tokens, Lucide React icons, dark-first theme, responsive sidebar with mobile hamburger drawer)
- Workflow visualization: embedded `@jentic/arazzo-ui` component with diagram/docs/split view modes
- Catalog workflow preview: direct links to `arazzo-ui.jentic.com` for workflows not yet imported locally
- SPA served with content negotiation — browser navigations get HTML, API calls get JSON
- Non-root container execution (configurable UID/GID)

### Catalog

- `GET /search` — BM25 full-text search over registered APIs/operations + workflows
- `GET /inspect/{id}` — unified capability inspection for operations and workflows
- `GET /apis/...` — list and get registered APIs with pagination
- `GET /workflows/...` — list and get registered workflows with content negotiation (formal Arazzo media types: `application/vnd.oai.workflows+json`, `application/vnd.oai.workflows+yaml`)
- `POST /import` — register APIs (URL/file/inline) and Arazzo workflows
- Capability IDs: `METHOD/host/path` format (no scheme, no spaces)
- Description abbreviation (≤3 sentences) for token efficiency in LLM consumers
- Vendor name extraction from API ID
- HATEOAS `_links` on all paginated and resource responses
- Public catalog integration (`jentic-public-apis` manifest sync)

### Execution

- Transparent broker proxy: `/{host}/{path}` (catch-all, registered last)
- Automatic credential injection: API key header, bearer, basic, multiple headers
- Simulate mode: `X-Jentic-Simulate: true` — returns mock 200 without calling upstream
- Policy enforcement: allow/deny rules per toolkit, first-match-wins
- Arazzo workflow execution via arazzo-engine (cloned at build time)
- All workflow steps route through the broker (single credential injection chokepoint)
- Workflow broker dispatch: `POST /{jpe_host}/workflows/{slug}` routes internally without external HTTP hop
- Execution traces: step-level data stored in SQLite (`executions` + `execution_steps`)
- Workflow error propagation: returns upstream HTTP status, `failed_step` detail, remediation hints
- **Async workflow execution** (RFC 7240): `Prefer: wait=N` header, job lifecycle (`pending → running → completed/failed`), `GET /jobs/{id}` polling, `DELETE /jobs/{id}` cancellation, optional webhook callbacks

### Access Control

- Toolkits: scoped credential bundles (renamed from "collections" in earlier design)
- Multi-key toolkits: one key per agent, individually revocable
- Per-key IP restrictions: CIDR array evaluated at request time
- Toolkit policies: allow/deny rules per toolkit with first-match-wins evaluation
- Permission requests: agents can request access they don't have; humans approve/deny

### Auth Flywheel

- Security scheme overlays: `POST /apis/{id}/scheme` registers pending overlay
- Auto-confirmation: on first successful broker 2xx, overlay flips to confirmed
- Handles APIs with missing/incorrect security schemes in their OpenAPI specs (Discourse pattern)
- Raw overlay registration: `POST /apis/{id}/overlays` for full control

### OAuth Brokers

- Pluggable OAuth broker system (`src/brokers/`)
- Pipedream Connect integration: 3,000+ APIs via managed OAuth proxy
- `POST /oauth-brokers` — register a broker (currently: `pipedream` type)

### API Design

- Tag taxonomy: search → inspect → execute → observe → toolkits → permissions → credentials → catalog
- Swagger UI tag ordering via `openapi_tags` in `main.py`
- Agent-oriented endpoint summaries: active voice, intent-matching up front
- Human auth: JWT + httpOnly cookies, 30-day TTL with auto-refresh, bcrypt passwords

---

## Known Gaps and Next Priorities

### UI / UX

**Overarching principle:** The human should spend as little time in the UI as possible. The agent tells the user when something needs their attention and gives them a link — the UI just needs to be the right landing page for that link. It also needs to serve secondary functions adequately (browsing available APIs, reviewing trace logs, auditing toolkit access), but agents should increasingly handle those on the human's behalf too.

**Gaps:**

- Human intervention actions (approve/deny a permission, enter a credential) should be completable from a single link the agent gives the user — taking them directly to the one action, with minimal friction. The agent handles the conversation; the UI just needs to land well.
- OAuth flows should be a single URL that handles the full dance and returns the human to wherever they came from.
- API browser is functional but bare — no filtering by credential status or toolkit access.
- Trace log view exists but offers limited filtering and no comparison between runs.
- No summary view of what a toolkit can currently do (see also: Toolkit capability summary).

**Technical sub-items:**
- ~166 `any` / `@ts-ignore` instances in the TypeScript UI — undermines type safety and makes refactoring risky.
- Limited error boundaries — Arazzo UI component has one; general page-level boundaries still needed to prevent unhandled errors crashing the whole UI.
- No accessibility (a11y) audit has been done.

**Remaining a11y debt (deferred):**
- Focus traps for modals/overlays
- ConfirmInline focus management
- `aria-live` for async status messages
- Skip-to-content link
- ARIA combobox pattern for search inputs

**Completed (v0.3):**
- TailwindCSS 3 → 4 upgrade with `@tailwindcss/vite` plugin (PostCSS and JS config removed)
- Design token system: single-file theme in `index.css` using shadcn/TW4-native `@theme inline` pattern; full HSL palette matching `@jentic/frontend-theme`
- All hardcoded Tailwind default colors replaced with semantic tokens
- All emoji icons replaced with Lucide React SVG components
- `outline-none` → `outline-hidden` for TW4 accessibility compliance

**Completed (v0.4):**
- UI testing infrastructure: Vitest browser mode (Chromium), MSW network mocking, axe-core a11y checks, `renderWithProviders` test utility
- 86 unit + integration tests across 10 test files (4 component, 1 hook, 5 page integration)
- Playwright E2E test suite (35 specs across 10 spec files)
- CI pipeline: `ui-tests` job in GitHub Actions (TypeScript check, Vitest, Playwright)

**Completed (v0.5):**
- Full page coverage: 143+ integration tests across 19 test files (all pages covered)
- AuthGuard redirect tests (7 tests)
- Mutation error tests with `createErrorHandler` utility
- Docker E2E: true end-to-end tests against real backend (setup flow, auth cycle, search)
- Accessibility fixes: htmlFor/id labels, aria-label on search inputs and icon buttons, aria-expanded on toggles, heading level corrections, role="alert" on error containers
- isError handling added to 5 pages (TracesPage, JobsPage, WorkflowsPage, OAuthBrokersPage, CatalogPage)
- Extracted AuthGuard component, replaced window.location.href with navigate()
- CI split: `ci-ui.yml` (path-filtered, fast feedback) + `ci-docker.yml` (always runs, Docker layer caching)

**Completed (v0.6):**
- UI component library: shadcn-style owned components (`Button`, `Input`, `Label`, `Textarea`, `Select`, `Dialog`, `EmptyState`, `PageHeader`, `ErrorAlert`, `LoadingState`, `BackButton`, `CopyButton`, `DataTable`, `Pagination`)
- `cn()` utility (clsx + tailwind-merge), shared `timeAgo`/`formatTimestamp`/`statusVariant`/`statusColor` utilities, `useCopyToClipboard` hook
- Native `<dialog>` for modals (zero new dependencies, browser-native accessibility)
- All 21 pages migrated: zero raw `<button>`, `<input>`, `<select>`, `<textarea>` elements in pages
- ESLint guardrails enforce UI library usage (`no-restricted-syntax` as errors in `src/pages/`)
- Deleted dead code (`TopBar.tsx`), removed duplicate utility functions across 6 files
- Barrel exports at `src/components/ui/index.ts`

### Versioning, Releases, and Updates

**✅ Completed:**
- Version source of truth: `APP_VERSION` flows from Docker build arg (set by CI from git tag via semantic-release)
- Versioned Docker tags: publish workflow creates full version (e.g. `0.4.1`), minor version (e.g. `0.4`), and `latest` tags for releases
- Release process: `semantic-release` workflow creates git tags, GitHub Releases with auto-generated changelogs, and triggers Docker publish
- Update detection: `GET /version` endpoint compares running version against latest GitHub release (cached 6h); admin UI shows "update available" banner when new version detected
- Docker images published compatible with amd64 and arm64 architectures
- Unstable builds: pushes to `main` branch create `:unstable` tag (not `latest`) for testing
- Database migrations: Alembic-based schema versioning with backward-compatible migrations; breaking changes communicated via GitHub release changelogs
- Automated dependency updates — `requirements.txt`, `package.json`, GitHub Actions are uptoupdated by Dependabot


### Local and Self-Hosted Services

**Broker can't route to local services**
The broker identifies upstream targets by requiring the first path segment to contain a dot (e.g. `api.stripe.com`). Hostnames like `localhost`, `my-service`, or `192.168.1.10` are rejected or treated as self-referential. This means agents cannot use Jentic Mini to call locally-running services — home automation APIs, internal tools, dev servers, or any self-hosted service without a public domain.

OpenAPI 3.1 provides a native mechanism for this via Server Variables: a spec can declare `servers[0].url` as `{serverUrl}` with a variable, allowing the base URL to be resolved at runtime. Jentic could honour this at import time.

Proposed approach:
- Allow `POST /import` to accept an explicit `base_url` override, regardless of what the spec declares in `servers`
- Assign a stable broker alias (e.g. `my-service.local`) derived from the import label, which the broker maps to the real local address
- Store the real target URL in the `apis.base_url` column (already exists); broker resolves it at request time rather than trusting the path segment literally
- This handles OpenAPI specs that declare `servers: [{url: "http://localhost:3000"}]` — currently the derived API ID is `localhost` and routing breaks entirely

Use cases: home automation (Home Assistant, etc.), internal APIs behind a firewall, local dev/test services, self-hosted tools (Gitea, Nextcloud, etc.).

### High Priority

**Step-to-step data transformation**
Arazzo runtime expressions (`$steps.X.outputs.Y`) pass data verbatim. When step 1 returns a large response (e.g. 500KB Discourse topics list) and step 2 is a token-limited API (OpenAI), the workflow fails with a 400.

Options:
- Custom Arazzo extension: a `transform` step type with jq/JSONPath filter
- JPE pseudo-operation: `POST /localhost/transform` that accepts `{data, filter}` and returns filtered result — agents can include this as a workflow step
- Input preprocessing: let callers pre-filter before invoking the workflow (workaround, not a fix)

**Test coverage — backend**
No backend automated tests yet. For a credential-handling proxy this is a reliability and security risk. Priorities:
- Vault encryption/decryption
- Auth middleware (key validation, IP allowlisting)
- Broker credential injection
- Policy enforcement (allow/deny evaluation)
- BM25 search ranking

**Complex multi-API workflow testing**
The broker-based Arazzo execution path (server URL rewriting + RuntimeParams) needs more testing with workflows that span multiple APIs with different auth schemes.

### Medium Priority

**Unauthenticated search**
Currently all endpoints require an API key. For cold-start / agent discovery without a key:
- Rate-limited `GET /search` without authentication
- Returns capability IDs and summaries only (no execute links until authenticated)
- Would enable agents to self-bootstrap without a pre-configured key

**Credential provisioning flow (human-in-the-loop)**
Current model: agent stores credentials directly via `POST /credentials`. This means the agent must hold the plaintext value — a security concern.

Better model:
1. Agent calls `POST /credentials/provision` with label + api_id (no value)
2. JPE generates a `user_url` where the human can enter the value directly
3. Agent polls `GET /credentials/{id}/status` until `provisioned`
4. Agent never sees the plaintext value

**OAuth2 bundled setup flow**
OAuth2 APIs (Spotify, Google, Slack user tokens, etc.) require multi-step human interaction for initial token grant. Pipedream broker exists but the first-party flow is incomplete. Proposed: agent calls `POST /credentials/oauth2/init`, JPE returns a single URL where the human completes the OAuth dance, JPE stores the access + refresh tokens, handles refresh automatically. Agent never touches the OAuth flow.

**Schema samples**
`POST /samples` endpoint: given an operation/workflow ID, return example request bodies and response shapes. Useful for simulate mode grounding (agents can see realistic mock data structures).

**~~llms.txt~~** ✅ Completed — `GET /llms.txt` endpoint and `AGENTS.md` added in v0.4.

**Agent-contributed catalog (workflow authorship flywheel)**
- Agents can submit workflows via `POST /import` — initially private to their toolkit
- Workflow can be "promoted" to public by admin
- Enables a community catalog of tested workflows
- Same flywheel model as auth overlays

**Toolkit capability summary**
`GET /toolkits/{id}/summary` — LLM-generated prose description of what a toolkit can do (which APIs are credentialed, what policies allow, what workflows are accessible). Reduces the need for agents to enumerate all capabilities manually.

### Low Priority / Design Decisions Pending

**Production workflow domain**
Workflow IDs currently use `localhost`. Production Jentic needs a canonical domain. Options: `jentic.net`, `functioncall.net`. Decision pending.

**Workflow step-level credential injection**
Currently credentials are injected at the toolkit level — the same credential is used for all steps that hit the same API. Some workflows may need different credentials for the same API host in different steps. Would require step-level credential overrides in the Arazzo spec or a JPE extension.

**HMAC request signing**
For higher-assurance credential binding: sign each broker request with an HMAC derived from the credential, verifiable at the upstream API without transmitting the raw key. Relevant for APIs that support request signing (AWS, Stripe webhook validation, etc.).

**Rate limiting and audit logging**
No rate limiting on any endpoint (including login and broker proxy). No audit trail for sensitive operations (credential creation, policy changes, key access). Both needed before any production exposure.

**Pagination model review**
All paginated endpoints currently use integer page numbers. Need to confirm: is cursor-based pagination ever needed for the APIs JPE proxies, or is page-number sufficient for the catalog/search use cases?

---

## Design Doc References

Architecture, auth flows, credential model, and workflow execution are documented in `docs/`:
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [AUTH.md](AUTH.md)
- [CREDENTIALS.md](CREDENTIALS.md)
- [WORKFLOWS.md](WORKFLOWS.md)
- [DECISIONS.md](DECISIONS.md)
