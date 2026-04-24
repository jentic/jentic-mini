# Phase 2 Validation — Backend Unit Test Coverage (Vault, Auth, Policy, Broker)

## Definition of Done

All of the following must be true before this branch is merged.

### 1. Full backend suite passes

```
pdm run test
```

Exits 0. Output includes all new unit-test files (`test_vault.py`, `test_auth_middleware.py`, `test_broker_injection.py`, `test_bm25.py`) and the extended `test_policy_engine.py` alongside the pre-existing integration/contract suite. Zero regressions on the existing tests.

### 2. New unit-test files run individually

```
pdm run test tests/test_vault.py tests/test_auth_middleware.py tests/test_broker_injection.py tests/test_policy_engine.py tests/test_bm25.py
```

Exits 0. Each new/extended file contributes at least one passing test per invariant listed in `requirements.md` *Constraints*.

### 3. Lint passes

```
pdm run lint
```

Exits 0. New test files comply with top-level-imports-only (ruff `PLC0415`) and no-private-cross-module-imports (ruff `PLC2701`). No new per-file-ignores are added in `pyproject.toml`.

### 4. CI backend workflow green

`.github/workflows/ci-backend.yml` passes on the PR. Both jobs — `lint` and `backend-tests` — must be green. The workflow is triggered automatically by changes under `tests/**`.

### 5. Each target module has a dedicated unit-test file

The following files exist and collectively cover the invariants listed in `requirements.md`:

- `tests/test_vault.py` — encrypt/decrypt round-trip; `InvalidToken` → `ValueError`; wrong-key decryption fails; `parse_route`
- `tests/test_auth_middleware.py` — `trusted_subnets()` append semantics; `is_trusted_ip()`; revoked-key rejection (401); IP-allowlist enforcement (403)
- `tests/test_broker_injection.py` — bearer; apiKey-in-header; basic; compound multi-header; unsupported query-param apiKey warning; `auth_type` fallback
- `tests/test_policy_engine.py` (extended) — engine-level default; effective default with `SYSTEM_SAFETY_RULES`; `operations` regex-list matching; invalid-regex fallback
- `tests/test_bm25.py` — exact-match ordering; partial-match `score > 0`; irrelevant-query empty result; mixed op + workflow results; determinism

### 6. No outbound network access in new tests

New test files contain no `httpx`, `requests`, `aiohttp`, or `urllib` call that escapes simulate mode. Broker-injection tests use `X-Jentic-Simulate: true` exclusively; no real upstream URL is contacted. The `_test_lifespan` skip set in `tests/conftest.py` (BM25 rebuild, self-registration, catalog refresh, OAuth broker loading) is unchanged — new tests do not re-enable any of those startup side-effects.

### 7. No src/ changes on the branch

```
git diff --name-only main...HEAD -- src/
```

Returns empty. The phase is test-only; any `src/` diff is a scope violation per `requirements.md` *Decisions*.

### 8. Human reviewer approval

PR approved by a human reviewer. This repo has no `CODEOWNERS` or `CONTRIBUTING.md` review policy; the gate is a standard GitHub review approval on a green CI.

## Not Required

- No UI tests — phase is backend-only; `ci-ui.yml` stays path-filtered off.
- No Playwright / E2E run.
- No `schemathesis` CLI run — the contract surface exercised today is `tests/test_openapi_contract.py`, which runs as part of `pdm run test`.
- No `ui/openapi.json` regeneration — no endpoint changes in this phase.
- No Alembic migration gates — no schema changes.
- No coverage-percentage threshold — `pytest-cov` is not configured and is explicitly out of scope for this phase.
- No manual curl or browser smoke — CI is the signal.
- No performance benchmarks.
- No `src/` refactors — helper promotions, broker-injection extraction, and policy-engine relocation are all explicitly deferred.
