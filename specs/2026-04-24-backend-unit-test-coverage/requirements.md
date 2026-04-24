# Phase 2 Requirements — Backend Unit Test Coverage (Vault, Auth, Policy, Broker)

## Scope

Add module-level unit tests for the highest-risk backend modules — vault encryption, auth middleware helpers, broker credential injection, policy-engine evaluation, and BM25 ranking — alongside the existing integration/contract suite in `tests/`. Tests are additive: one new file per module (`tests/test_<module>.py`), plus an extension of the already-unit-shaped `tests/test_policy_engine.py`. No `src/` code changes; every target is exercised through its existing public surface.

The phase closes an explicit early-access risk named in `specs/mission.md` (`## Current State`) and called out again in `specs/tech-stack.md` (`## Testing`): the backend has integration and contract tests but no module-level unit tests over the credential-handling, perimeter-auth, and access-control code paths that define the system's security posture.

## Out of Scope

- `src/` refactors — no helper promotions (e.g. `_ip_allowed` → `ip_allowed`), no extraction of the broker injection loop into `src/brokers/injection.py`, no relocation of `check_policy` out of `src/routers/toolkits.py`
- OAuth broker credential paths through `src/brokers/pipedream.py` — the phase covers native bearer / apiKey / basic / multi-header schemes only
- Coverage-percentage thresholds — `pytest-cov` is not configured, and wiring it is explicitly deferred
- New integration tests — the existing integration/contract suite is the baseline this phase is *additive to*
- Any UI / E2E / Playwright / docs changes

## Decisions

### Test-only, no src/ changes
Every target is reached through its public surface: `encrypt`/`decrypt` in `src/vault.py`; `trusted_subnets`, `is_trusted_ip`, `default_allowed_ips`, `client_ip` in `src/auth.py`; `check_policy` in `src/routers/toolkits.py`; `build`/`search` in `src/bm25.py`; broker credential injection via the existing simulate-mode code path (`X-Jentic-Simulate: true`) that short-circuits before any aiohttp call. Private helpers (`_ip_allowed`, `_fernet`, `_find_credential_for_host`'s inline header loop) are tested indirectly through their public callers. Rationale: the phase is framed as test coverage; mixing test work with structural refactors increases review surface and fights the ruff `PLC2701` rule on private cross-module imports.

### Flat file layout under `tests/`
New files follow the existing flat naming convention (`tests/test_<module>.py`). No new subdirectory (`tests/unit/`), no separate light-weight conftest. New files skip the heavy session fixtures from `tests/conftest.py` (`client`, `admin_session`, `agent_key`, `agent_only_client`) and only use them where a TestClient-shaped test is unavoidable (the auth middleware IP/revoked-key cases, which must go through the full app lifespan to exercise middleware ordering).

### Hand-built BM25 fixture
Use a small in-test dict fixture (~6 operations, ~2 workflows) matching the `METHOD/host/path` capability-ID shape and the field contract declared in `src/bm25.py` (`summary`, `description`, `path`, `method`, `_vendor` for operations; `name`, `involved_apis` for workflows). Rejected alternative: snapshotting `data/catalog_manifest.json` — would bind tests to external catalog churn and defeat the "no network in CI" constraint.

### Behavior-focused, invariant-per-test
Every load-bearing invariant listed under *Constraints* below gets at least one direct assertion. Coverage is measured by the explicit invariant checklist, not a line-coverage percentage.

### Policy engine tested in place
`check_policy` lives in `src/routers/toolkits.py` today. `tests/test_policy_engine.py` already imports it directly and uses the correct unit-test shape (plain pytest classes, no fixtures) — the phase extends that file instead of creating a new one or moving the engine.

## Constraints

Load-bearing invariants from `specs/mission.md` and `specs/tech-stack.md` that this phase must preserve and — where relevant — witness with an assertion.

- **Secrets never touch the agent** (mission.md `Core Invariants`) — Vault tests assert encrypt/decrypt round-trip, `InvalidToken` → `ValueError("Failed to decrypt credential")`, and wrong-key decryption failure. Credential loss is terminal (there is no recovery path), so pinning Fernet behavior is directly load-bearing.
- **Trusted-subnet append semantics** (tech-stack.md `Constraints and Conventions`) — `trusted_subnets()` must always include the default RFC-1918 + loopback set and *append* `JENTIC_TRUSTED_SUBNETS` extras. Self-hosters rely on this perimeter; a silent replace would open unintended remote access.
- **Two-actor authentication** (mission.md `Core Invariants`) — Agent keys are revocable and IP-restricted; a compromised agent key cannot self-escalate. Tests assert revoked keys (`revoked_at IS NULL` filter) and IP-allowlist enforcement.
- **Policy engine default action** (tech-stack.md `Constraints and Conventions`) — First-match-wins; engine-level default is allow, but `SYSTEM_SAFETY_RULES` are appended by the runtime, making the effective default deny-writes-and-sensitive-paths. Tests pin both the engine-level default and the effective default so the semantics cannot drift silently.
- **Capability ID format `METHOD/host/path`** (mission.md `Core Invariants`) — BM25 fixtures use this exact shape so the tests stay honest to the API contract that agents persist.
- **`conftest.py` DB_PATH ordering** (tech-stack.md `Testing`) — New test files must not break the rule that `DB_PATH` is set in `tests/conftest.py` before any `src.*` import. New files add no import-time side effects; they rely on the existing conftest.
- **Top-level imports only; no private cross-module imports** (tech-stack.md `Constraints and Conventions`) — Ruff `PLC0415` / `PLC2701`. Tests import only public symbols; private helpers are exercised through their public callers, not imported directly.
- **CI passes without external network access** (phase body) — No outbound HTTP from new tests. Broker injection exclusively uses `X-Jentic-Simulate: true`; BM25 uses in-memory fixtures; vault and policy tests are pure.

## Context

This phase exists now because the backend is explicitly flagged as incomplete on module-level unit coverage — `specs/mission.md` lists "incomplete backend unit test coverage (integration and contract tests exist; module-level unit tests are a gap)" as a known early-access risk. For a credential-handling proxy whose whole value proposition is "secrets never touch the agent," the fact that the Fernet vault, the perimeter auth middleware, the broker's credential-injection dispatch, and the policy engine have no direct unit tests is a reliability and security concern in its own right.

The phase also sits on the critical path to Phase 3 (TypeScript Arazzo Runner Migration), which explicitly depends on it: `specs/roadmap.md` notes "test coverage needed before a risky runtime swap." The invariants this phase locks down become regression fences for the runner swap — a workflow that routes every step through the broker must behave identically on the TS runner, and we need tests that catch divergence at the module level, not only at the HTTP boundary.

Cross-references for reviewers: `docs/AUTH.md` (endpoint-level auth model), `docs/CREDENTIALS.md` (Fernet vault contract), `docs/ARCHITECTURE.md` (broker + injection flow), `.claude/rules/testing.md` (test organization and commands).

## Stakeholder Notes

- **Security-conscious teams** — Directly served. The phase tests the single-chokepoint credential injection and perimeter auth — exactly the surfaces this audience relies on. Trusted-subnet append semantics and revoked-key handling are the two tests they would write first.
- **Self-hosters** — Directly served. Fernet vault integrity + trusted-subnet perimeter lock down the self-hosted threat model; a wrong-key decryption test makes the "losing the vault key means losing access" invariant enforceable, not just documented.
- **Phase 3 implementers (TypeScript Arazzo Runner Migration)** — Served indirectly. Broker injection + policy evaluation become a testable contract before the Python → TypeScript runner swap, so a behavioral regression during that work surfaces as a failing module-level test rather than an integration flake.
