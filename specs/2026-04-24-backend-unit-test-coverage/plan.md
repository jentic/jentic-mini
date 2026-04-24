# Phase 2 Plan — Backend Unit Test Coverage (Vault, Auth, Policy, Broker)

## Group 1 — Vault encryption tests

1. Create `tests/test_vault.py`. Top-level imports only: `from src.vault import encrypt, decrypt, parse_route` plus `from cryptography.fernet import Fernet`.
2. Add round-trip tests: generate a Fernet key, monkeypatch `JENTIC_VAULT_KEY`, assert `decrypt(encrypt(plaintext)) == plaintext` for several input shapes (ASCII, unicode, empty string, long blob); assert `encrypt(x) != x`.
3. Add `InvalidToken` test: `decrypt("not-a-fernet-token")` raises `ValueError` whose message contains `"Failed to decrypt credential"` (pins the contract at `src/vault.py` `decrypt()`).
4. Add wrong-key test: encrypt under key A, swap `JENTIC_VAULT_KEY` to key B, assert `decrypt(...)` raises `ValueError`. Locks the "vault-key-loss is terminal" invariant.
5. Add `parse_route` tests covering the route shapes the module documents (simple path, path with variables, leading/trailing slash normalization).

## Group 2 — Auth helper tests

6. Create `tests/test_auth_middleware.py`. Top-level imports: `from src.auth import trusted_subnets, is_trusted_ip, default_allowed_ips, client_ip`.
7. `trusted_subnets()` append-semantics tests: with `JENTIC_TRUSTED_SUBNETS` unset, the returned set equals the default RFC-1918 + loopback set (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `::1/128`); with extras set, the returned set is the union (order-independent, deduped); defaults are never removed regardless of what `JENTIC_TRUSTED_SUBNETS` contains.
8. `is_trusted_ip()` tests: loopback IPv4, loopback IPv6, each RFC-1918 range, a public IPv4, a public IPv6; with and without extras env var.
9. `default_allowed_ips()` returns a JSON-encoded list matching `trusted_subnets()` at call time (per-call read, not import-time).
10. Middleware IP-rejection test via the existing `client` + `agent_key_header` fixtures: issue a key with `allowed_ips = ["203.0.113.0/24"]`, call any authed endpoint from the default test IP, assert HTTP 403.
11. Revoked-key test: issue a key, revoke it, call an authed endpoint with that key, assert HTTP 401 (covers the `ck.revoked_at IS NULL` filter in `APIKeyMiddleware.dispatch`).

## Group 3 — Broker credential injection tests

12. Create `tests/test_broker_injection.py`. Reuse the simulate-mode pattern from `tests/test_credential_injection.py` — set `X-Jentic-Simulate: true` to short-circuit the broker before any upstream HTTP call.
13. Seed a toolkit + credential for each scheme shape using the existing conftest factories (as `test_credential_injection.py` does): bearer, apiKey-in-header, basic, and compound (Secret + Identity, multi-header).
14. For each scheme, issue a simulated broker request and assert the simulated echo response reports the injected headers exactly — including the `Authorization: Basic <base64(user:pass)>` shape for basic auth.
15. Query-param apiKey: seed a credential whose scheme declares `in: query`, issue a simulated request, assert the broker logs/returns the unsupported-query-param warning (pins the behavior at the injection helper's unsupported branch).
16. `auth_type` fallback test: seed a credential with no explicit scheme blob and `auth_type = 'basic'`, assert the broker still produces the base64 Basic header via the fallback path (pins the fallback branch).

## Group 4 — Policy engine tests (extend existing)

17. Extend `tests/test_policy_engine.py` — do not create a new file; it already uses the module-level unit-test shape (`from src.routers.toolkits import check_policy`, plain pytest classes).
18. Add engine-level default-action cases: with `agent_rules = []` and *no* `SYSTEM_SAFETY_RULES` appended, `check_policy(..., "GET", "/x")` returns `(True, "Default action: allow")`. Locks the literal default in `check_policy`.
19. Add effective-default cases using `SYSTEM_SAFETY_RULES` appended: writes on arbitrary paths denied; sensitive regex paths (`admin|pay|billing|webhook|secret|token`) denied for any method; non-sensitive reads allowed.
20. Add `operations` regex-list matching cases: a rule whose `operations` list contains multiple regexes is first-match-wins across the list; a non-matching regex falls through to the next rule.
21. Add invalid-regex fallback case: a rule with a malformed regex does not crash policy evaluation; it is skipped and evaluation continues (pins the invalid-regex guard).

## Group 5 — BM25 ranking tests

22. Create `tests/test_bm25.py`. Top-level imports: `from src.bm25 import build, search`.
23. Build a hand-crafted fixture: ~6 operation dicts and ~2 workflow dicts. Operations use the `METHOD/host/path` capability-ID shape with the required fields (`summary`, `description`, `path`, `method`, `_vendor`); workflows use `name`, `involved_apis`.
24. Assertions: exact-match query against an operation summary returns that operation first; synonym/partial query returns relevant docs with `score > 0`; irrelevant query returns `[]` (the `score > 0` filter excludes zero-score results); workflows and operations both appear in mixed-result queries.
25. Determinism test: `build(ops)` then two `search(q)` calls return identical result ordering.

## Group 6 — Verify

26. `pdm run test tests/test_vault.py tests/test_auth_middleware.py tests/test_broker_injection.py tests/test_policy_engine.py tests/test_bm25.py` exits 0.
27. `pdm run test` exits 0 (full suite, zero regressions on existing integration/contract tests).
28. `pdm run lint` exits 0. New files comply with top-level-imports-only (`PLC0415`) and no-private-cross-module-imports (`PLC2701`).
29. `ci-backend.yml` is green on the PR (triggered by `tests/**` path filter).
30. Audit new test files: no `httpx`, `requests`, `aiohttp`, or `urllib` call escapes simulate mode; no catalog manifest fetch; no Pipedream API call.
