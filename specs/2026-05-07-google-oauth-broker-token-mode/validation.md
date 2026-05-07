# Phase 24 Validation — Google OAuth Broker (Token Mode)

## Definition of Done

All of the following must be true before the **implementation** branch (the PR that closes #336) is merged. This spec-scaffold PR carries no code and is reviewed for the spec content; the gates below apply to the follow-up implementation PR.

### 1. Backend lint clean

```
pdm run lint
```

Exit code 0. Both `ruff check` and `ruff format --check --diff` produce no findings.

### 2. New backend tests pass

```
pdm run test -- tests/test_brokers_google.py tests/test_oauth_broker_exchange_code.py tests/test_admin_api_keys.py -v
```

Exit code 0. Each of the three new test files runs and asserts at minimum:

- `tests/test_brokers_google.py` — `exchange_code` happy path persists `oauth_broker_accounts` row and returns `ExchangeResult`; `exchange_code` re-grant without a fresh `refresh_token` does not clobber the existing one with `NULL`; `get_token` cache hit returns cached token without HTTP; `get_token` cache miss + valid refresh persists new access token and returns it; `get_token` `invalid_grant` returns `None`; `has_scopes` subset returns `True`, superset returns `False`, missing row returns `False`; `covers` row-present returns `True`, no-row returns `False`. Upstream Google calls mocked via `monkeypatch.setattr(GoogleOAuthBroker, "_token_post", spy)` (no real network).
- `tests/test_oauth_broker_exchange_code.py` — `POST /oauth-brokers` with `body.type='google'` happy path returns 200; missing `client_id` returns 400; `POST /oauth-brokers/{id}/exchange-code` happy path against a stubbed broker returns 200 with `{provider_user_id, granted_scopes, api_hosts}`; non-Google broker returns 400; simulated Google upstream error returns 502.
- `tests/test_admin_api_keys.py` — human-session caller mints a `tk_` key (200, plaintext returned in body once); agent-key caller is rejected 403; the minted key authenticates a subsequent `X-Jentic-API-Key` request to a public endpoint.

### 3. Pipedream regression intact

```
pdm run test -- tests/test_oauth_broker_lifecycle.py tests/test_oauth_broker_default_user.py -v
```

Exit code 0. Both files run unmodified and pass. Confirms "Pipedream broker code path is untouched".

### 4. OpenAPI / UI client sync gate

```
pdm run test -- tests/test_openapi_contract.py::test_ui_openapi_matches_served_spec -v
```

Exit code 0. The committed `ui/openapi.json` matches the live `/openapi.json`. Failure here means the regenerate step (plan.md task 38) was skipped or partial.

### 5. Generated TypeScript client compiles

```
npm --prefix ui run lint && npx --prefix ui tsc --noEmit
```

Both exit code 0. Proves the regenerated `ui/src/api/generated/` files compile under strict TypeScript and pass ESLint.

### 6. Documentation updated in the same PR

The diff must include all of the following changes:

- `docs/oauth-broker.md` — new "Token-mode brokers" section covering `GoogleOAuthBroker`, the seven new schema columns, `auth_type='broker_oauth'`, the `/exchange-code` endpoint, the multi-instance `redirect_uri` strategy, and the `has_scopes()` Protocol addition. The existing "Migration Path: Pipedream → Jentic OAuth" section reworded from wholesale-replacement language to broker-by-broker swap.
- `specs/tech-stack.md` — the "Pipedream is the only first-class implementation today" sentence (current lines 67-68) updated to describe Pipedream (proxy-mode) and Google (token-mode) as the current first-class brokers.
- `CLAUDE.md` — "OAuth brokers (`src/brokers/`)" section mentions `google.py` alongside `pipedream.py`.
- `docs/auth.md` — `POST /admin/api-keys` listed under human-session-only privileged operations; `POST /oauth-brokers/{broker_id}/exchange-code` boundary recorded (admin OR human-session OR has-toolkit).

### 7. Phase 24 entry removed from the roadmap

```
grep -nE '^## Phase 24' specs/roadmap.md
```

No matches. Per the lifecycle rule at `specs/roadmap.md:35-37`, the Phase 24 block must be deleted (not renumbered) when this phase ships. Surrounding phase numbers (23, 25, …) stay as they are.

### 8. Live broker-create smoke

**Prerequisite:** `cookies.txt` contains a valid human-session cookie obtained via a prior `POST /user/login` against the dev instance with admin credentials. With the dev server up (`pdm run uvicorn src.main:app --port 8900 --reload`):

```
curl -sS -X POST http://localhost:8900/oauth-brokers \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"id":"google","type":"google","config":{"client_id":"test","client_secret":"test","redirect_uri":"http://localhost:8900/oauth/callback"}}' \
  | python3 -m json.tool
```

HTTP 200. Body contains `"id": "google"`, `"type": "google"`, and `"redirect_uri": "http://localhost:8900/oauth/callback"`. `client_secret` MUST NOT appear in the response.

## Not Required

- **Real Google OAuth round-trip in CI.** All Google upstream calls are mocked via `monkeypatch.setattr` on `GoogleOAuthBroker` methods (matching the Pipedream test pattern at `tests/test_oauth_broker_default_user.py:81-85`). No real client credentials in CI; no `respx`/`httpx_mock` library introduced.
- **Token-revocation flow tests.** Out of scope per `specs/roadmap.md` Phase 24 body and #336 "Out of scope". Worth a follow-up issue, not gated here.
- **UI Playwright E2E for a Google broker form.** UI work is a follow-up — no React component for Google ships in this phase. The OpenAPI regen (Definition of Done item 4) keeps the generated TypeScript in sync; no E2E spec is required.
- **Schemathesis contract pass.** Schemathesis is in dev deps but not wired into CI (verified — `grep -rn schemathesis .github/workflows/` is empty; `tests/test_openapi_contract.py:55` documents the FastAPI-TestClient incompatibility). The OpenAPI sync gate (item 4) is the contract enforcement that exists today.
- **Rate limiting and audit-log entries** for `POST /admin/api-keys` and `POST /oauth-brokers/{id}/exchange-code`. Pre-production concerns deferred to roadmap Phase 11.
- **Pipedream refactor.** No `_maybe_inject_pipedream_oauth` extraction, no replacement of the `hasattr(_b, "proxy_request_with_account")` registry walk, no `find_broker()` first-call rework. The Pipedream branch at `src/routers/broker.py:843-961` stays byte-for-byte.
- **Migration of existing `auth_type='oauth2'` credentials to `'broker_oauth'`.** The two coexist with distinct semantics; no automatic migration.
- **Generic `NativeOAuthBroker` base class.** `GoogleOAuthBroker` is concrete; abstraction will land when a second token-mode broker is built (GitHub or Microsoft per the roadmap). Issue #104's `oauth_native_*` table proposal is not pursued.
