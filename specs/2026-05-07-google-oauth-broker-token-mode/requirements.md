# Phase 24 Requirements — Google OAuth Broker (Token Mode)

## Scope

Phase 24 ships `GoogleOAuthBroker` as the first **token-mode** OAuth broker in `src/brokers/`. The broker stores Google client credentials, runs the OAuth authorization-code exchange against `https://oauth2.googleapis.com/token`, persists refresh tokens (Fernet-encrypted), and refreshes access tokens transparently when asked for one. Credential injection in the broker proxy chain gains a third branch — `auth_type='broker_oauth'` — that sits alongside the existing `pipedream_oauth` path; both leave the existing direct-credential paths in `src/routers/broker.py` untouched.

The phase is additive. The schema gains seven `NULL`-defaulted columns across `oauth_brokers` and `oauth_broker_accounts` (no data migration). `_SUPPORTED_TYPES` in the OAuth-broker router gains `"google"`. Two new endpoints land: `POST /oauth-brokers/{broker_id}/exchange-code` (operator's control plane forwards an OAuth `code` over the internal network into a Mini instance, supporting a single fleet-wide redirect URI) and `POST /admin/api-keys` (programmatic toolkit-key minting, independently shippable per #336). Nothing in `src/brokers/pipedream.py`, the Pipedream connect-link/sync flow, or the Pipedream credential branch in `src/routers/broker.py` (`broker.py:843-961`) changes.

## Out of Scope

- **Generalisation across providers.** GitHub, Microsoft, generic RFC-6749, dynamic client registration, PKCE, or a `NativeOAuthBroker` base class. The class is concretely Google: hardcoded `oauth2.googleapis.com` URLs, a Google-only scope→api_host map (Gmail/Calendar/Drive/Sheets/Docs + OpenID), no provider-pluggable auth/token URLs.
- **UI work.** The Pipedream-specific broker form in `ui/src/pages/CredentialsPage.tsx` is not generalised in this phase; a follow-up issue covers the broker-create UX. The OpenAPI client regen *is* required so the generated TypeScript stays in sync, but no React component for Google lands.
- **Migration of `auth_type='oauth2'` credentials to `'broker_oauth'`.** The two coexist with distinct semantics; `'oauth2'` remains "pre-obtained, no refresh".
- **Token-revocation flow on broker delete; rate limiting on the new endpoints; audit-log entries.** Pre-production concerns deferred to Phase 11.
- **Pipedream refactor of any kind.** No `_maybe_inject_pipedream_oauth` extraction, no replacement of the `hasattr(_b, "proxy_request_with_account")` registry walk, no `find_broker()` first-call rework. The Pipedream branch stays byte-for-byte intact.

## Decisions

### `auth_type='broker_oauth'` as a parallel sentinel
Reuse the precedent set by `'pipedream_oauth'`: a reserved internal `auth_type` that agents cannot create via `POST /credentials` (already enforced by the `Literal` in `src/models.py:47-61`, which excludes both sentinels). The `models.py` `Literal` stays unchanged; `'broker_oauth'`, like `'pipedream_oauth'`, is populated only by the broker exchange-code path and matched in `src/routers/broker.py` by string comparison. Keeps the two broker paths visibly parallel and makes the no-overlap with `'oauth2'` (which retains its own semantics) explicit.

### Google-specific implementation, no abstraction yet
`GoogleOAuthBroker` is a dataclass that hardcodes Google's token endpoint, refresh semantics, scope→api_host map, and id-token decoding. The CTO directive for this phase is to leave Pipedream as its own special path; per the SDD "shippable slice" rule, this phase does not introduce a generic `NativeOAuthBroker` base. The follow-up brokers identified by the roadmap (GitHub, Microsoft) will replicate the pattern; the right time to extract a base is when the second concrete impl lands. Issue #104's `oauth_native_*` table proposal is not pursued — the additive columns on `oauth_brokers`/`oauth_broker_accounts` cover the same ground without a parallel table set.

### Schema additions are NULLable; no data migration
Seven columns across two tables, all `NULL`-defaulted. Existing Pipedream rows leave them blank; the new Google flow populates them. Migration `0005_google_oauth_broker.py` is a pure-DDL revision off `0004_credential_routes.py`, with the defensive `try/except` pattern from `alembic/versions/0004_credential_routes.py:209-218` so re-runs on existing dev databases do not error. Migration is self-contained: no `src.*` imports.

### `oauth_broker_accounts.app_slug='google'` and `account_id=provider_user_id`
The current schema has `app_slug` and `account_id` as `NOT NULL` (post `0002_broker_accounts_account_id_unique`). Rather than relax those constraints, Google rows populate `app_slug='google'` (constant per broker type) and `account_id=<provider_user_id>` (the `sub` claim from the OAuth `id_token`). Preserves the unique constraint `UNIQUE(broker_id, external_user_id, api_host, account_id)` and avoids destabilising Pipedream's invariant.

### Add `OAuthBrokerRegistry.get(broker_id)` for direct lookup
Issue #336's `_maybe_inject_broker_oauth` pseudo-code calls `registry.get(cred.broker_id)`. The current registry has no such method; existing callers (e.g. `src/routers/oauth_brokers.py:551`) use `next((b for b in registry.brokers if b.broker_id == bid), None)`. Add a one-line `get(broker_id) -> OAuthBroker | None` to `OAuthBrokerRegistry`; the inline `next(...)` callers stay unchanged (no opportunistic refactor).

### `has_scopes()` declared on the Protocol; concrete brokers implement
`typing.Protocol` cannot ship runnable defaults — method bodies are `...`. Declare `async def has_scopes(self, external_user_id, required_scopes) -> bool: ...` on the `OAuthBroker` Protocol. `PipedreamOAuthBroker` implements it returning `True` (preserves existing behaviour and keeps Pipedream tests green). `GoogleOAuthBroker` implements the real subset check against the persisted `scopes` JSON column.

### Single Google account per `(broker_id, external_user_id)`
Google's incremental authorization (`include_granted_scopes=true`) means a single connection accumulates scopes; one `oauth_broker_accounts` row per `(broker_id, external_user_id)` covers all granted hosts. This is asymmetric with Pipedream's `(broker_id, external_user_id, api_host, account_id)` key (Pipedream allows multiple accounts per host) but matches Google's semantics. The asymmetry is recorded so future readers do not try to align them.

### `redirect_uri` is per-broker, not derived from `JENTIC_PUBLIC_HOSTNAME`
`redirect_uri` lives in the new `oauth_brokers.redirect_uri` column and is configured at broker-registration time. This deliberately diverges from `build_absolute_url()` (`src/utils.py:8-26`) so a single fleet-wide redirect URI plus `POST /exchange-code` works for self-hosted multi-instance deployments — the operator's control plane receives the redirect, then forwards the `code` into each Mini instance over the internal network. Documented in the new section of `docs/oauth-broker.md`.

### `POST /admin/api-keys` is human-only and lives in a new `src/routers/admin.py`
Two-actor auth model (per `docs/auth.md`): there is no admin API key; `docker exec` is the only superuser path. The endpoint requires `Depends(require_human_session)` and returns the plaintext `tk_` once. New router file `src/routers/admin.py`, registered in `src/main.py` *before* the broker catch-all and added to `_HUMAN_ONLY_OPERATIONS` at `main.py:476-508`. Independently shippable per #336 — can be split into a separate PR if review prefers, but lands in this phase by default.

### `POST /oauth-brokers/{broker_id}/exchange-code` is agent-callable
Matches the auth pattern of sibling agent-facing OAuth-broker routes (e.g. `src/routers/oauth_brokers.py:545-549`): admin OR human-session OR has-toolkit. The operator's control plane needs to forward codes from any Mini instance, including those reached only via toolkit auth.

## Constraints

- **Pipedream broker code path is untouched.** `src/brokers/pipedream.py`, `proxy_request_with_account` at `src/routers/broker.py:934`, the `hasattr(_b, "proxy_request_with_account")` registry walk at `broker.py:923-926`, the connect-link/connect-callback flow at `oauth_brokers.py:521-803`, the `_extract_pipedream_config` helper at `oauth_brokers.py:205-228`, and `API_ID_TO_PD_SLUG` at `pipedream.py:71-157` all stay byte-identical. Phase 24 adds branches and helpers, never edits or refactors existing Pipedream code.
- **Broker catch-all stays last in `src/main.py:448`.** New routers (`admin_router`, plus the new `/exchange-code` route inside the existing `oauth_brokers_router`) must register before line 448 or the catch-all will swallow them.
- **Two-actor auth model.** No admin API key; `POST /admin/api-keys` is gated by `Depends(require_human_session)` only. `POST /oauth-brokers/{broker_id}/exchange-code` matches the agent-callable pattern (admin OR human-session OR has-toolkit).
- **Fernet vault contract on all new secret columns.** `refresh_token_enc` and `access_token_enc` on `oauth_broker_accounts`, plus the existing `client_secret_enc` on `oauth_brokers`, all round-trip through `src.vault`. Decrypt only at use; never persist or log plaintext. Vault key (`JENTIC_VAULT_KEY`) is the only recovery path.
- **Alembic is the schema source of truth.** Migration `0005_google_oauth_broker.py` runs at startup via `run_migrations()` in `src/main.py` lifespan; `src/db.py` is not the schema file. The migration must not import from `src/*` (per the comment at `alembic/versions/0004_credential_routes.py:39`).
- **Capability ID format stable.** `METHOD/host/path`. The Google scope→api_host map produces real public hostnames (`gmail.googleapis.com`, `sheets.googleapis.com`, `www.googleapis.com`, `docs.googleapis.com`, `openidconnect.googleapis.com`); broker requests routed through these hostnames keep capability IDs valid and do not collide with Pipedream's `googleapis.com/<service>` `api_id` shape.
- **OpenAPI contract stability.** Adding `"google"` to `_SUPPORTED_TYPES` and adding two endpoints is additive. The `_PIPEDREAM_CONFIG_EXAMPLE`/`_CREATE_DESCRIPTION` docstrings on `POST /oauth-brokers` (`oauth_brokers.py:46-118`) need restructuring so the published OpenAPI description advertises both broker types' config shapes accurately. The `tests/test_openapi_contract.py::test_ui_openapi_matches_served_spec` gate enforces drift between `/openapi.json` and `ui/openapi.json`.
- **Top-level imports only.** The new `src/brokers/google.py`, `src/routers/admin.py`, and any helpers must follow `.claude/rules/python-code-style.md` (Ruff `PLC0415`).

## Context

Pipedream is currently the only OAuth broker in Mini, and it is genuinely proxy-mode — Pipedream holds the upstream tokens and proxies HTTP calls through its Connect API. The `OAuthBroker` Protocol at `src/oauth_broker.py:31-63` was designed to support a second mode (token-mode: broker returns a `Bearer`, the consumer in `src/routers/broker.py` injects the header and forwards locally), but no implementation exists. Phase 24 lights up that path with Google.

Self-hosted Mini deployments routinely want Gmail / Calendar / Drive / Sheets / Docs without a Pipedream intermediary; today the only available path runs through Pipedream's hosted infrastructure, which contradicts Mini's "credentials never leave the host" principle (`specs/mission.md`). Adding `GoogleOAuthBroker` directly closes this gap and exercises every part of the token-mode contract — refresh, scope-coverage check, code exchange, id-token decoding — under realistic conditions. Once the pattern works for Google, follow-up brokers (`GitHubOAuthBroker`, `MicrosoftOAuthBroker`) become URL/scope-format swaps, and an abstraction can be extracted at that point. Issue #104 proposed a generic "Native OAuth broker" with separate `oauth_native_*` tables; Phase 24 keeps the schema additive on the existing tables and defers the broader generic-broker question.

The `POST /oauth-brokers/{broker_id}/exchange-code` endpoint is the load-bearing addition for multi-instance self-hosted deployments: a single fleet-wide redirect URI hosted by an operator's control plane receives the OAuth `code`, then forwards it over the internal network into each Mini instance, instead of every instance needing its own externally-routable redirect URI. `docs/oauth-broker.md` and `docs/auth.md` are the primary documentation surfaces; `specs/tech-stack.md` lines 67-68 (the "Pipedream is the only first-class implementation" sentence) and `CLAUDE.md` ("OAuth brokers" section) need refreshing to reflect the new state.

## Stakeholder Notes

- **CTO** — directive for this phase: "leave Pipedream as its own special thing." Satisfied by the "Google-specific implementation, no abstraction yet" decision and the "Pipedream broker code path is untouched" constraint; design overlap with #104 is resolved by deferring the generic-broker question rather than acting on it now.
- **Operators of multi-instance self-hosted Mini deployments** — need a single fleet-wide OAuth redirect URI. Satisfied by `POST /oauth-brokers/{broker_id}/exchange-code` plus the per-broker `redirect_uri` decision.
- **Agents using a toolkit bound to Google credentials** — no behaviour change at the call site; the agent continues to use `X-Jentic-API-Key` and the broker injects the `Authorization: Bearer <google-access-token>` header transparently. The new `auth_type='broker_oauth'` is invisible to the agent.
