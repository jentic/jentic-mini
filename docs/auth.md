# Authentication & Authorisation

## Overview

Jentic Mini uses two distinct authentication mechanisms for two distinct actors:

| Actor | Mechanism | Purpose |
|---|---|---|
| **Human** | bcrypt password → httpOnly JWT cookie | Admin operations, approving permission requests, managing keys, approving agent registrations |
| **Agent (OAuth, recommended)** | RFC 7591 Dynamic Client Registration → JWT-bearer assertion → `Authorization: Bearer at_…` | Search, inspect, execute, toolkit-scoped operations bound to the registered agent identity |
| **Agent (legacy)** | `X-Jentic-API-Key: tk_xxx` | Search, inspect, execute, toolkit-scoped operations on a static, per-toolkit shared secret |

For the OAuth path see [agent-identity.md](agent-identity.md) — it covers
discovery, registration, JWT-bearer assertion shape, refresh-token rotation,
revocation, and admin lifecycle (approve / disable / deregister).

There is **no admin API key** (no `JENTIC_API_KEY` env var). CLI access to the container is
already a stronger trust boundary — anyone with `docker exec` can read the database directly.
Adding a secret env var on top creates a credential that can be leaked without adding security.

---

## Human Authentication

### Account model

Single root account — no multi-user, no roles. One human owns the instance.

**Account creation is one-time.** `POST /user/create` returns `410 Gone` after the first call.

### Endpoints

| Method | Path | Auth required | Notes |
|---|---|---|---|
| `POST` | `/user/create` | None (one-time) | Creates root account and issues session cookie (auto-login). 410 after first call. |
| `POST` | `/user/login` | None | Returns httpOnly JWT cookie on success. |
| `POST` | `/user/token` | None | OAuth2 password grant for Swagger UI; returns Bearer JWT. |
| `POST` | `/user/logout` | Human session | Clears cookie. |
| `GET` | `/user/me` | Optional | Returns current auth/session context; works with no auth. |

**There is no password-reset API.** No "forgot password" link, no email reset,
no security questions. If the password is lost, the rescue path is `docker exec`
into the container and editing the SQLite database directly — either rewrite
`users.password_hash` (bcrypt the new password first) or drop the `users` row
and clear the `account_created` setting to re-enable one-time `POST /user/create`.
`docker exec` is deliberately the only superuser path (see Overview).

### JWT

- Algorithm: `HS256`, secret generated at first startup and stored in the settings table
- Expiry: **30-day sliding window** — token expires 30 days after last use
- Rolling: on every authenticated request, if the token is older than 1 day, a fresh 30-day token is issued via `Set-Cookie` on the response
- Storage: httpOnly, SameSite=Strict cookie — not accessible to JavaScript
- Effect: the human stays logged in indefinitely as long as they use the UI within any 30-day window

### What currently requires a human session

Human-session-only enforcement is applied per-route (via `Depends(require_human_session)`) on
sensitive endpoints. Key examples:

- `POST /toolkits/{toolkit_id}/access-requests/{req_id}/approve`
- `POST /toolkits/{toolkit_id}/access-requests/{req_id}/deny`
- `PATCH /toolkits/{toolkit_id}`
- `DELETE /toolkits/{toolkit_id}`
- `PUT|PATCH /toolkits/{toolkit_id}/credentials/{cred_id}/permissions`
- `POST|PATCH|DELETE /oauth-brokers...` admin endpoints

`POST /default-api-key/generate` requires a human session — it is no longer
an agent self-enrollment endpoint. See [Toolkit-key issuance](#toolkit-key-issuance)
below.

Not all write operations are currently human-session-only: some routes allow agent keys when
policy allows (for example credential writes with explicit credential policy rules).

---

## Agent Authentication

### Key format

All agent keys use the prefix `tk_` (toolkit key) followed by 32 hex characters
(`secrets.token_hex(16)`). Example: `tk_a1b2c3d4e5f67890abcdef1234567890abcd`.

Keys are passed via header:
```
X-Jentic-API-Key: tk_a1b2c3d4e5f67890abcdef1234567890abcd
```

### Default API key

Every instance has exactly one **default API key**, bound to the default
toolkit. It is created by an admin via the UI (or
`POST /default-api-key/generate` from a human session) and shared with
the agent out of band. The default key can be used for normal agent
flows (search/inspect/execute and toolkit-scoped operations).

### Additional keys

Additional `tk_xxx` keys can be issued per toolkit. Keys are individually revocable and support
per-key IP restrictions (`allowed_ips` CIDR list).

New keys are **never issued unrestricted**: if no explicit allowlist is supplied, `allowed_ips`
defaults to the trusted-subnets list (RFC-1918 + loopback + any `JENTIC_TRUSTED_SUBNETS` extras).
A key row with `NULL` or empty `allowed_ips` is still evaluated against the trusted-subnets list
at request time — subnet is the perimeter, not the absence of restriction.

### Scopes (planned)

Fine-grained scope assignment is planned (`api_keys` table). Current implementation is primarily
toolkit identity + route-level human-session guards + credential policy checks.

---

## Unauthenticated Access

Some endpoints are intentionally open — no key required:

| Path | Reason |
|---|---|
| `GET /health` | Discovery; explicit setup instructions for agents |
| `GET /.well-known/oauth-authorization-server` | RFC 8414 OAuth metadata for agent DCR |
| `POST /register` | RFC 7591 Dynamic Client Registration (yields `pending` until human approves) |
| `POST /oauth/token` | OAuth token endpoint — signature on the assertion is the auth |
| `POST /user/create`, `POST /user/login`, `POST /user/token` | Initial/setup and human login flows |
| `GET /user/me` | Session/auth context probe (works with or without auth) |
| `GET /docs`, `/redoc`, `/openapi.json`, `/llms.txt` | API documentation |
| `GET /static/*` | Static assets |
| `/{host}/{path}` (broker) | Transparent conduit — upstream auth is upstream's problem |
| `POST /workflows/{slug}` | Open passthrough workflow execution |

**Broker and workflow execution with no key:** `request.state.toolkit_id = None`. The broker
skips credential injection and policy enforcement, then forwards the request clean. If the
upstream API requires auth and no credentials are present, the upstream returns 401/403, which
the broker passes through unmodified. Jentic Mini does not gate access to third-party APIs that
don't require credentials.

**Search, inspect, catalog** currently require a key. Public catalog visibility (returning only
`public: true` results to unauthenticated callers) is a separate future design — see the main
design document.

---

## Onboarding flows

### OAuth (recommended)

The agent registers itself, the human approves, the agent mints a token.
This is the path documented at [agent-identity.md](agent-identity.md).

```
# 1. Agent discovers endpoints.
GET /.well-known/oauth-authorization-server
→ 200 {"issuer": "...", "registration_endpoint": "...", "token_endpoint": "...", ...}

# 2. Agent registers (RFC 7591) with its Ed25519 public key in JWKS form.
POST /register
{"client_name": "my-agent",
 "jwks": {"keys": [{"kty":"OKP","crv":"Ed25519","x":"...","kid":"k1"}]}}
→ 201 {"client_id": "agnt_…",
       "registration_access_token": "rat_…",
       "registration_client_uri": ".../register/agnt_…",
       "status": "pending"}

# 3. Agent polls until a human approves the registration in the admin UI.
GET /register/{client_id}
Authorization: Bearer rat_…
→ {"status": "approved", ...}

# 4. Agent signs a JWT-bearer assertion (RFC 7523) with the matching private key
#    and exchanges it for an access token.
POST /oauth/token
grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=eyJhbGciOiJFZERTQSIs...
→ 200 {"access_token": "at_…", "refresh_token": "rt_…", "expires_in": 900, ...}
```

The agent then sends `Authorization: Bearer at_…` on every request.
Refresh tokens rotate per call and reuse of a consumed `rt_` revokes the
entire family (RFC 6749 BCP §4.14). Humans can disable, deny, or
deregister an agent from the admin UI's Agents page — disable revokes all
issued tokens, deny is terminal, deregister soft-deletes the row.

### Toolkit-key issuance

The legacy path: a human creates a `tk_xxx` key in the admin UI and
shares it with the agent out of band. There is no longer an
unauthenticated self-enrollment endpoint.

1. Human signs in to the admin UI.
2. **Toolkits → default → Keys → Generate key** (or `POST
   /default-api-key/generate` from a human session for the default
   toolkit; `POST /toolkits/{toolkit_id}/keys` for additional keys).
3. The `tk_xxx` value is shown **once only** by the API/UI. It is also
   stored in `toolkit_keys.api_key` for runtime lookup, so anyone with
   direct database access can read it.
4. The human pastes the key into the agent's configuration. The agent
   sends it as `X-Jentic-API-Key: tk_xxx`.

Additional keys can be issued per toolkit. Keys are individually
revocable and support per-key IP restrictions (`allowed_ips` CIDR list).

### Subnet defaults for issued toolkit keys

`JENTIC_TRUSTED_SUBNETS` is **not** an authentication check on the
key-generation endpoints. It controls the **default `allowed_ips`
applied to a newly-issued `tk_xxx` key** when no explicit allowlist is
provided — `POST /default-api-key/generate`, `POST /toolkits/{id}/keys`,
and the bootstrap internal key all read this value. The broker then
enforces those per-key ranges at request time, returning 403 if the
caller's IP is outside the key's allowlist.

Default ranges (always present, cannot be removed):

- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`
- `127.0.0.0/8`
- `::1/128`

Extended via `JENTIC_TRUSTED_SUBNETS` env var (comma-separated CIDR
list). The env var **appends** to the built-in defaults — setting it
never removes the RFC-1918/loopback entries.

#### Why no subnet check on `/default-api-key/generate` itself?

The endpoint used to need a subnet guard because it was an anonymous
self-enrollment path. It now requires a logged-in admin session and
only rotates an already-claimed default key (fresh instances get `410
default_toolkit_key_disabled`), so an admin session is a strictly
stronger gate than the subnet check ever was. The env var's role on
issued keys is unchanged.

---

## Key Regeneration (Rescue)

If the agent loses its key:

1. Human logs into UI → **Keys** section → **Regenerate default key**
2. Old key is revoked (soft delete via `revoked_at`)
3. New `tk_xxx` key is issued and shown once
4. Human copies it into agent configuration

The UI also supports issuing an *additional* key without revoking the old one — useful if the
agent is mid-task and you don't want to interrupt it.

---

## Threat Model

**Primary concern: prompt injection causing destructive writes.**

Concrete attack chain (now mitigated):
1. Attacker injects prompt into data the agent processes (e.g. an email)
2. Agent is instructed to elevate its own Gmail credential access
3. Agent calls `POST /toolkits/{toolkit_id}/access-requests` requesting a grant/permission change
4. Without mitigation: agent could approve its own escalation request
5. Agent forwards emails to attacker's address

**Mitigation:** `approve` / `deny` are human-session-only:
- `POST /toolkits/{toolkit_id}/access-requests/{req_id}/approve`
- `POST /toolkits/{toolkit_id}/access-requests/{req_id}/deny`

An agent key cannot call these routes. The human approves via the `/approve/{toolkit_id}/{req_id}` UI flow with a valid JWT session.

**Secondary concern: leaked agent key used by a third party.**

Mitigated by per-key IP restriction (CIDR allowlist on `toolkit_keys` row). Recommended: set
`JENTIC_TRUSTED_SUBNETS` and configure key IP restrictions to local subnets only.

---

## Database tables (auth-related)

### `users`

Single root account.

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `username` | TEXT UNIQUE | |
| `password_hash` | TEXT | bcrypt |
| `created_at` | TIMESTAMP | |

### `settings`

Key-value store for instance configuration.

| Key | Value |
|---|---|
| `jwt_secret` | Random 32-byte hex, generated at first startup |
| `default_key_claimed` | `1` after first `POST /default-api-key/generate` |
| `account_created` | `1` after first `POST /user/create` |

### `toolkit_keys`

One row per issued agent key. For conceptual model see `docs/architecture.md`; for exact schema
and current columns see Alembic migrations in `alembic/versions/`.

Key columns in current schema: `api_key` (the `tk_xxx` string), `toolkit_id`, `allowed_ips`, `revoked_at`, `created_at`.
Planned scopes are tracked separately via `api_keys` (not yet active for toolkit key enforcement).

---

## Runtime dependencies (current)

Auth currently uses:

- `bcrypt`
- `python-jose[cryptography]`

These are declared in `pyproject.toml`.
