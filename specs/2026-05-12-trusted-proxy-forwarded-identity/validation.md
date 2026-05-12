# Phase 28 Validation — Trusted-Proxy Forwarded Identity Authentication

## Definition of Done

All of the following must be true before this branch is merged.

### 1. Trusted-proxy integration tests pass

```
pdm run test tests/test_trusted_proxy_auth.py -v
```

Exit code 0. Every test mapped to the six acceptance criteria from #366 plus the `X-Forwarded-Prefix` gating cases passes:

1. **Default (no env)** — `/toolkits` returns 401 without a session cookie; `/user/me` returns 200 with `logged_in: false`.
2. **Env set + trusted peer + header present** — `/user/me` returns 200 with `logged_in: true` and `username` equal to the header value; a `users` row exists with `password_hash IS NULL` and `created_via = 'trusted_proxy'`.
3. **Env set + trusted peer + header absent** — a protected endpoint returns 401.
4. **Env set + untrusted peer + header present** — 401; `caplog` records a WARN on logger `jentic.auth` whose message includes the peer IP and the rejected header.
5. **Env set + trusted peer + spoofed `X-Forwarded-For`** — still authenticated (peer IP is the gate, not `X-Forwarded-For`).
6. **JIT-provisioned account at `/user/login` and `/user/token`** — both return 401 with body `{"error": "invalid_credentials"}`; no 500.
7. **Trusted peer + `X-Forwarded-Prefix: /foo`** — `scope["root_path"]` is `/foo`; routes resolve under the prefix.
8. **Untrusted peer + `X-Forwarded-Prefix: /foo`** — `scope["root_path"]` stays unset; WARN recorded on `jentic.auth`.

### 2. Existing test suite passes

```
pdm run test
```

Exit code 0. No regression in `tests/test_auth_boundary.py`, `tests/test_root_path.py`, `tests/test_auth_boundary_comprehensive.py`, or the wider suite.

### 3. Lint passes

```
pdm run lint
```

Exit code 0.

### 4. Migration round-trips cleanly

```
PYTHONPATH=. pdm run python -m alembic upgrade head
PYTHONPATH=. pdm run python -m alembic downgrade -1
PYTHONPATH=. pdm run python -m alembic upgrade head
```

All three exit 0.

### 5. Schema reflects the migration

```
PYTHONPATH=. pdm run python -c "import sqlite3, os; db = sqlite3.connect(os.environ['DB_PATH']); cols = {r[1]: r[3] for r in db.execute('PRAGMA table_info(users)')}; assert 'created_via' in cols and cols['password_hash'] == 0; print('schema ok')"
```

Exits 0 and prints `schema ok` — `created_via` column present, `password_hash` NULLable (notnull flag is `0`).

### 6. README documents both new env vars

```
grep -F "JENTIC_TRUSTED_PROXY_HEADER" README.md
grep -F "JENTIC_TRUSTED_PROXY_NETS" README.md
```

Each exits 0.

### 7. PR #369's deferred-gap note is removed from README

```
grep -F "#366" README.md
```

Exits 1 (no match). The `> **Deployment note…`-style paragraph that references issue #366 as a future fix is gone.

### 8. `docs/auth.md` documents the third human auth path and the schema change

```
grep -F "JENTIC_TRUSTED_PROXY_HEADER" docs/auth.md
grep -F "created_via" docs/auth.md
```

Each exits 0. A "Trusted-Proxy Forwarded Identity" subsection exists under Human Authentication; the `users` schema documentation reflects `created_via` and NULLable `password_hash`.

### 9. `ForwardedPrefixMiddleware` docstring is current

```
grep -F "future peer-IP-gated" src/main.py
```

Exits 1 (no match). The stale "future peer-IP-gated trust boundary" language is gone.

### 10. Phase 28 roadmap heading carries the ` ✅` suffix

```
grep -F "## Phase 28 — Trusted-Proxy Forwarded Identity Authentication ✅" specs/roadmap.md
```

Exits 0. The single space before U+2705 is load-bearing per the `specs/roadmap.md` lifecycle rule — `Title✅` (no space) silently fails this grep.

## Not Required

- No UI tests (Vitest / `npm run test:run`). Phase 28 makes no `ui/src/**` changes.
- No Playwright E2E. The SPA login-skip behaviour is validated server-side via the `/user/me` response shape; no new browser flow is introduced.
- No schemathesis CLI run. No new OpenAPI paths or response-shape changes; `ui/openapi.json` is not regenerated.
- No update to `tests/test_auth_boundary_comprehensive.py`'s `EXPECTED_OPERATION_COUNT = 86` sentinel — Phase 28 adds zero HTTP routes.
- No manual reverse-proxy smoke test. Integration tests with `TestClient(client=(ip, port))` cover the CIDR gate without needing a live Caddy / nginx.
