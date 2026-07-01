> Issue: jentic/jentic-one#638

## Context

Operators can only configure the Pipedream credential provider by hand-editing
the backend YAML (`config/*.yaml` → `credentials.providers`) and restarting the
server. The backend already ships a working `PipedreamProvider`, a
`PipedreamProviderConfig` schema, a synchronous `ProviderRegistry`, and a
feature-flagged UI. What is missing is a runtime, API-driven path to store and
activate that config.

This issue introduces the **first slice of dynamic, DB-backed configuration**:
generic `admin config providers` endpoints + a Go CLI command tree that let an
operator set/get/list provider configs at runtime. The provider config (with an
AES-256-encrypted `client_secret`) is persisted in the **admin** database in a
generic `provider_configs` table keyed by name, treating `pipedream` as just one
`{name}`. A successful write rebuilds the in-process `ProviderRegistry` so the
change takes effect without a restart. Because `control` (which owns the
registry) may not import `admin` ORM models, the registry reads the dynamic
config through a **shared raw-SQL helper** against the admin DB. Finally, the UI
drops its build-time `VITE_CREDENTIALS_PIPEDREAM` flag and discovers Pipedream
availability from the existing `GET /credentials/providers` endpoint.

The endpoints, table, and helper are deliberately generic so future YAML configs
(SSO IdP settings, general app config) can migrate to the same pattern.

## Files to Change

### Backend — storage & shared helper
1. `src/jentic_one/admin/core/schema/provider_configs.py` — **new** `ProviderConfigRecord` ORM model (`provider_configs` table): `name` PK, `config_json` JSON, audit columns via `AuditableMixin`.
2. `src/jentic_one/admin/core/schema/__init__.py` — register the new model so Alembic autogenerate/metadata discovery sees it.
3. `src/jentic_one/migrations/admin/versions/z5a6b7c8d9e0_add_provider_configs.py` — **new** admin migration creating `provider_configs` (down_revision = current head `y4z5a6b7c8d9`).
4. `src/jentic_one/admin/repos/provider_config_repo.py` — **new** static, flush-only repository (`upsert`, `get`, `list_all`) for `ProviderConfigRecord`.
5. `src/jentic_one/shared/provider_config_store.py` — **new** shared helper exposing a raw parameterized-SQL reader (`load_provider_configs(session)` / `load_provider_config(session, name)`) returning decoded JSON. This is the cross-module boundary-safe path the registry uses; mirrors `src/jentic_one/shared/lookups.py`.

### Backend — registry refresh (control + context)
6. `src/jentic_one/control/services/credentials/providers/registry.py` — extend `from_config` (or add `from_config_and_dynamic`) to merge dynamic provider configs (already-decoded dicts) on top of the YAML config when building providers.
7. `src/jentic_one/shared/context.py` — add a `refresh_providers()` method that rebuilds `self._providers` from YAML config + the dynamic store, and make the `providers` property load dynamic config on first build. Holds the registry instance that the PUT handler swaps.

### Backend — admin web layer
8. `src/jentic_one/admin/web/schemas/provider_configs.py` — **new** Pydantic request/response schemas: a generic `ProviderConfigSetRequest`/`ProviderConfigResponse`, plus per-name payload validation for `name="pipedream"` (maps to `PipedreamProviderConfig` fields) and the redacted GET response.
9. `src/jentic_one/admin/services/provider_config_service.py` — **new** service: validates the payload by name, encrypts `client_secret` via `ctx.encryption`, upserts through the repo, triggers `ctx.refresh_providers()`, and returns redacted views for get/list.
10. `src/jentic_one/admin/web/routers/config.py` — **new** router with `PUT /admin/config/providers/{name}`, `GET /admin/config/providers/{name}`, `GET /admin/config/providers` (list), guarded by an admin permission.
11. `src/jentic_one/admin/web/deps.py` — add `get_provider_config_service`.
12. `src/jentic_one/admin/web/app.py` — register `config.router` in `get_routers()`.
13. `openapi/control/control.openapi.yaml` & `ui/openapi.json` — regenerated via `make openapi` (do not hand-edit).

### CLI — Go `admin config providers` tree
14. `cli/internal/cmd/admin.go` — **new** `newAdminCmd` (parent `admin` command + a `config`/`providers` group).
15. `cli/internal/cmd/admin_providers.go` — **new** `set`/`get`/`list` subcommands; `set {name}` takes `--project-id`, `--client-id`, `--environment`, etc., and prompts securely (no echo) for `client_secret`.
16. `cli/internal/adminclient/client.go` — **new** typed HTTP client wrapping `httpx` for the three admin config endpoints.
17. `cli/internal/cmd/root.go` — register `newAdminCmd(app)` under a new `admin` group in `newAPIRootCmd` (additive).

### UI — drop build-time flag, use discovery
18. `ui/src/modules/credentials/config.ts` — remove `isPipedreamEnabled()`/flag; change `providerOptions()` to accept the discovered provider list (or expose a pure builder) so Pipedream is included only when discovery reports it `configured`.
19. `ui/src/modules/credentials/components/CredentialTypeFields.tsx` & `CreateCredentialDialog.tsx` — call `useProviders()` and pass the discovered providers into `providerOptions(...)`.
20. `ui/src/modules/credentials/__tests__/config.test.ts` — replace `VITE_CREDENTIALS_PIPEDREAM` stub-based tests with discovery-driven cases.
21. `ui/src/vite-env.d.ts` — remove the `VITE_CREDENTIALS_PIPEDREAM` declaration.

## Build Order

### 1. Storage: model, migration, repository
1.1. Add `ProviderConfigRecord` (file 1): `name: Mapped[str]` PK (`String`), `config_json: Mapped[dict] = mapped_column(JSON())`, inherit `AuditableMixin, AdminBase`. The JSON holds the **full provider config with the secret already encrypted** (plaintext secret never persisted).
1.2. Register it in `core/schema/__init__.py` (file 2).
1.3. Write the migration (file 3) with `down_revision = "y4z5a6b7c8d9"` (verified current admin head). Follow the existing PostgreSQL+SQLite-compatible style used by `c2d3e4f5a6b7_add_users_secrets_invites.py` (audit columns, index on `created_at`/`created_by`).
1.4. Add `ProviderConfigRepository` (file 4) — static methods `upsert(session, *, name, config_json, created_by)`, `get(session, name)`, `list_all(session)`; flush-only, never commits.
1.5. **Verify:** `make test-integration` (or run the new migration against fixtures) creates the table; a small repo round-trip test stores and reads back JSON.

### 2. Shared raw-SQL reader (boundary-safe)
2.1. Create `src/jentic_one/shared/provider_config_store.py` (file 5) modeled on `shared/lookups.py`: `async def load_provider_configs(session) -> dict[str, dict]` and `load_provider_config(session, name)` using `sqlalchemy.text("SELECT name, config_json FROM provider_configs ...")` with bound params. Returns the stored JSON dicts (secret still encrypted) — **no ORM import**, so `control` can use it without violating boundaries.
2.2. **Verify:** `make test-arch` (`tests/arch/test_module_boundaries.py`) still passes; add an integration test that seeds a row via the repo and reads it back via the shared helper.

### 3. Registry refresh wiring (control + context)
3.1. In `registry.py` (file 6), add a path that accepts pre-decoded dynamic configs (dicts) and validates each into the right `ProviderConfig` (discriminated by `kind`) before `_build_provider`. Dynamic entries override YAML entries of the same name. Decryption of `client_secret` happens here (or in the service that hands configs in) using the encryption service — keep `.get()` synchronous.
3.2. In `context.py` (file 7), add `async def refresh_providers(self)` that: opens an `admin_db` session, calls `load_provider_configs`, decrypts secrets via `self.encryption`, and rebuilds `self._providers = ProviderRegistry.from_config(...)` merged with dynamic configs. Make the lazy `providers` property perform the same dynamic load on first access (so a fresh process picks up DB config). Decide and document the secret-decryption seam (recommended: service decrypts before building, or registry receives plaintext `SecretStr`).
3.3. **Verify:** unit test that a registry built from YAML + a dynamic pipedream dict resolves `providers.get("pipedream")`; `.get()` remains synchronous (no `await` inside it).

### 4. Admin API endpoints
4.1. Schemas (file 8): generic `ProviderConfigSetRequest` (free-form fields per provider) + a validator that, for `name=="pipedream"`, coerces/validates against `PipedreamProviderConfig` (requiring `project_id`, `client_id`, `client_secret`, optional `environment`, `connect_base_url`, `expiry_skew_seconds`). `ProviderConfigResponse` redacts `client_secret` to `***`.
4.2. Service (file 9): `set(name, payload, *, identity)` — validate by name, encrypt `client_secret`, build `config_json`, `upsert` in an `admin_db.transaction()`, record audit (follow `user_service` audit pattern), then `await ctx.refresh_providers()`. `get(name)` / `list()` — read via repo, return redacted views.
4.3. Router (file 10) + deps (file 11) + app registration (file 12): `PUT /admin/config/providers/{name}`, `GET /admin/config/providers/{name}`, `GET /admin/config/providers`. Guard with `get_current_identity(required_permissions=[...])` using an appropriate admin/config permission (reuse an existing high-privilege permission or add a `config:write`/`config:read` pair consistent with the permission catalog).
4.4. Run `make openapi` to regenerate specs (file 13).
4.5. **Verify:** `make lint typecheck test`; integration test hitting `PUT` then `GET` (asserting redaction) and confirming `ctx.providers.get("pipedream")` resolves after the PUT.

### 5. Go CLI `admin config providers`
5.1. Add `adminclient` (file 16) wrapping `httpx.Client` with `SetProvider(ctx, token, name, body)`, `GetProvider(...)`, `ListProviders(...)`; resolve base URL + token via the existing `agentSession`/identity helpers in `cmd/common.go`.
5.2. Build the command tree (files 14–15): `admin` → `config` → `providers` with `set {name}`, `get {name}`, `list`. `set` defines flags (`--project-id`, `--client-id`, `--environment`, `--connect-base-url`, …) and prompts for `client_secret` with `huh.EchoModePassword` (reuse the pattern in `cli/internal/cmd/credential_prompt.go`); never accept the secret as a plain flag value that lands in shell history (optionally allow stdin).
5.3. Register `newAdminCmd(app)` in `root.go` (file 17), additively, in a new `admin` group.
5.4. **Verify:** `cd cli && go build ./... && go test ./...`; manual `jentic admin config providers set pipedream --project-id … --client-id …` (prompts for secret) then `get`/`list` show redacted output.

### 6. UI discovery (remove build-time flag)
6.1. Refactor `config.ts` (file 18): delete `isPipedreamEnabled()` and the env flag; make `providerOptions(type, discovered)` include `PIPEDREAM_OPTION` only when the discovered provider list contains an entry with `id === 'pipedream'` and `configured === true`.
6.2. Update consumers (file 19) to call `useProviders()` and feed the discovery result into `providerOptions(...)`. Keep `isManagedProvider`/`managedProviderUnavailableMessage` (still useful for error UX).
6.3. Remove the flag declaration (file 21) and rewrite tests (file 20) to drive behavior from discovery payloads instead of env stubs.
6.4. **Verify:** `cd ui && npm run codegen` (if specs changed), `npm run lint`, `npm test` (vitest); confirm Pipedream appears in the OAuth2 picker only when discovery reports it configured.

## Verification

1. **Migration:** Run admin migration to head against fixtures (`make start-fixtures` + migrate) — `provider_configs` table exists with audit columns; `make test-integration` green.
2. **Boundaries:** `make test-arch` passes — `control` still does not import `admin` ORM; the registry reads dynamic config only through `shared/provider_config_store.py`.
3. **Encryption at rest:** After a `PUT pipedream`, inspect the stored row — `config_json.client_secret` is ciphertext (decryptable via `EncryptionService`), never plaintext.
4. **API round-trip:** `PUT /admin/config/providers/pipedream` with valid body returns 200; `GET /admin/config/providers/pipedream` returns the config with `client_secret` redacted to `***`; `GET /admin/config/providers` lists `pipedream`. Invalid pipedream payload (missing `project_id`/`client_id`) returns 422.
5. **Runtime refresh (no restart):** In one process, `GET /credentials/providers` does **not** list pipedream; after `PUT`, the same endpoint reports pipedream `configured: true` and `ProviderRegistry.get("pipedream")` resolves — proving `refresh_providers()` rebuilt the synchronous registry.
6. **CLI:** `go build`/`go test` in `cli/`; `jentic admin config providers set pipedream …` prompts for the secret without echo, `get`/`list` show redacted output and exit 0.
7. **UI:** `npm run lint` + `npm test` in `ui/`; with discovery returning pipedream `configured:true` the picker shows the Pipedream option, and with it absent the option is hidden — all without `VITE_CREDENTIALS_PIPEDREAM`. Grep confirms the flag is fully removed.
8. **Full gate:** `make check` (lint + typecheck + score + unit/arch tests) passes; `make openapi` produces no uncommitted diff.

## Follow-ups / known limitations

**Cross-process (multi-process topology) propagation.** `refresh_providers()`
rebuilds the registry on the *Context of the process that handled the admin
write*. In the **combined** deployment (one process serving admin + control +
broker), that is the same in-memory registry the control/broker paths resolve
against, so a `PUT` takes effect immediately. In a **parts/multi-process**
topology (admin, control, registry as separate services — see
`deploy/helm/values/local-parts.yaml`), the control/broker processes do **not**
share the admin process's Context:

- They are granted only their own DB (`_expand_allowed_dbs(["control"])` →
  `{"control"}`), so their boot-time refresh is skipped (`_is_allowed("admin")`
  is `False`) and they never see an admin `PUT` from another process.
- Net effect: in parts mode the managed Pipedream option only reflects DB state
  captured at the control process's boot; `GET /credentials/providers` and the
  connect flow won't pick up a later `PUT` until that process restarts.

This is acceptable for the current default (combined) deployment and is called
out in the Configuration OpenAPI tag and `Context.refresh_providers()` docstring.
A proper fix (a follow-up issue) is one of: (a) have control read the DB on the
discovery/connect path instead of relying on an in-memory registry, or (b) a
notify/poll mechanism (e.g. LISTEN/NOTIFY or a short TTL re-read) so all
processes converge after a write.
