---
type: constitution
section: roadmap
generated_by: spec-driven-agent
generated_at: 2026-04-23T00:00:00Z
sources:
  - @docs/ROADMAP.md
  - @docs/ARCHITECTURE.md
  - @README.md
  - @src/main.py
  - @.claude/templates/sdd/constitution/roadmap.example.md
confidence: high
---

# Roadmap

Phases are intentionally small — each one must be a **shippable, independently reviewable, and
testable slice of work**.

This roadmap starts from the current repository state (v0.9.0, Early Access) and describes
the next meaningful increments. Phases are ordered by declared priority in `docs/ROADMAP.md`.
Each phase is a vertical slice: it touches whatever layers are needed (backend, frontend, tests)
to deliver a complete, observable capability.

**Source of truth for completed work:** `docs/ROADMAP.md` (Completed section).  
This roadmap only covers **what comes next**.

---

## Phase 1 — Local Service Routing

**Goal:** Allow the broker to route to non-public hostnames (`localhost`, bare names, IP addresses).  
**Depends on:** none (self-contained broker change)  
**Priority:** High (explicitly listed in `docs/ROADMAP.md`)

- Add optional `base_url` override to `POST /import`, stored in `apis.base_url`
- Assign a stable broker alias (e.g. `my-service.local`) derived from the import label
- Modify the broker to resolve the target URL from `apis.base_url` at request time rather than trusting the path segment literally
- Update the dot-based host detection to allow configured aliases to bypass it
- Add integration tests: import a spec with `base_url`, broker a request, verify it routes to the overridden URL

## Phase 2 — Backend Unit Test Coverage (Vault, Auth, Policy, Broker)

**Goal:** Cover the four highest-risk backend modules with unit/integration tests.  
**Depends on:** none  
**Priority:** High (noted as a reliability and security risk in `docs/ROADMAP.md`)

- Tests for vault encryption/decryption (`src/vault.py`)
- Tests for auth middleware: key validation, revoked keys, IP allowlisting (`src/auth.py`)
- Tests for broker credential injection: bearer, apiKey, basic, multi-header (`src/brokers/`)
- Tests for policy engine: allow/deny rule evaluation, first-match-wins, default action (`src/validators.py` / policy logic)
- All tests must pass in CI without external network access

## Phase 3 — TypeScript Arazzo Runner Migration

**Goal:** Replace Python `arazzo-runner` with the TypeScript implementation from `jentic-arazzo-tools`.  
**Depends on:** Phase 2 (test coverage needed before a risky runtime swap)  
**Priority:** High (active development gap; Python runner is interim)

- Add the TypeScript runner package to the Docker build (installed at build time, not in the final runtime PATH)
- Implement a Python shim that invokes the TS runner as a subprocess, passing `RuntimeParams` for broker URL rewriting
- Validate broker URL rewriting works identically for multi-step workflows spanning multiple APIs with different auth schemes
- Remove the PyPI `arazzo-runner` dependency once the shim is fully validated
- Add integration tests with a multi-step workflow fixture (two APIs, two credentials)

## Phase 4 — API Surface Alignment with Jentic Standards

**Goal:** Align key API surface areas with the Jentic standard to improve cross-edition compatibility.  
**Depends on:** none (can proceed in parallel with Phase 3)  
**Priority:** High (noted as needed for cross-edition compatibility and migration ease)

- Audit and align: authentication header names, pagination format, error response schema, capability ID format in responses
- Document any breaking changes clearly in a migration note
- Update the OpenAPI schema (`/openapi.json`) to reflect aligned structures
- Verify the `schemathesis` contract tests still pass after changes
- Update `AGENTS.md` and `llms.txt` if any agent-facing endpoint formats change

## Phase 5 — Step-to-Step Data Transformation

**Goal:** Allow workflow steps to filter or transform large upstream responses before passing them to the next step.  
**Depends on:** Phase 3 (TypeScript runner migration)  
**Priority:** High (workflows currently fail when step 1 returns large payloads to token-limited APIs)

- Implement a JPE pseudo-operation `POST /localhost/transform` accepting `{data, filter}` and returning filtered JSON (jq/JSONPath filter)
- Register `localhost` as a known broker alias (internal routing, no upstream call)
- Allow Arazzo workflow steps to reference the transform operation
- Add integration tests: a two-step workflow where step 1 returns a large response and step 2 receives a filtered subset
- Document the transform pseudo-operation in `docs/WORKFLOWS.md`

## Phase 6 — Human-in-the-Loop Credential Provisioning

**Goal:** Allow agents to initiate credential provisioning without ever seeing plaintext values.  
**Depends on:** none  
**Priority:** Medium (current model requires agent to hold plaintext at creation time)

- Add `POST /credentials/provision` accepting `{label, api_id}` (no value), returning a `user_url`
- Add `GET /credentials/{id}/status` returning `{status: "pending" | "provisioned"}`
- Add a UI page at the `user_url` where a human can enter the credential value directly
- Store the value through the vault on human submission
- Poll endpoint and UI page must both work correctly; add integration test for the full flow

## Phase 7 — UI Deep-Link Actions (Single-URL Human Interventions)

**Goal:** Any human intervention (approve permission, enter credential, reconnect OAuth) should be completable from a single URL the agent can provide.  
**Depends on:** Phase 6 (credential provisioning URL is one such deep link)  
**Priority:** Medium (UX gap described in `docs/ROADMAP.md`)

- Add direct deep-link routes for: approve/deny a permission request, enter/update a specific credential, initiate OAuth reconnect for a specific account
- Each route lands on a focused, minimal UI showing only the required action
- Agent can construct the URL from data already available (toolkit ID, request ID, credential ID)
- Add Playwright E2E tests for each deep-link flow

## Phase 8 — TypeScript Strictness (Eliminate `any` and `@ts-ignore`)

**Goal:** Reduce the ~166 `any`/`@ts-ignore` instances in the UI to zero.  
**Depends on:** none  
**Priority:** Medium (tech debt; makes refactoring risky and undermines type safety)

- Enable stricter TypeScript compiler options incrementally (`noImplicitAny` as a starting point)
- Fix type errors file by file; prefer introducing typed interfaces over casting
- Add a CI check that fails on new `any` or `@ts-ignore` additions (`@typescript-eslint/no-explicit-any` as error)
- Do not break existing test coverage during the migration

## Phase 9 — UI Page-Level Error Boundaries

**Goal:** Prevent unhandled errors in any page from crashing the entire SPA.  
**Depends on:** none  
**Priority:** Medium (UX risk; currently only the Arazzo UI component has a boundary)

- Add a React error boundary wrapping each top-level page component
- Error boundary shows a user-facing fallback with a "Reload" action
- Add Vitest tests verifying that a thrown error in a page does not propagate to parent layout
- Add at least one Playwright E2E test simulating a page-level error and verifying the fallback renders

## Phase 10 — Accessibility Audit and Remediation

**Goal:** Make the admin UI meet basic WCAG 2.1 AA accessibility requirements.  
**Depends on:** Phase 9 (stable error handling reduces noise in a11y testing)  
**Priority:** Medium (no a11y audit has been done; specific debt listed in `docs/ROADMAP.md`)

- Add focus traps to all modal/overlay dialogs
- Implement `aria-live` regions for async status messages (loading, success, error)
- Add skip-to-content link on the layout shell
- Fix ARIA combobox pattern for search inputs
- Add ConfirmInline focus management (return focus to trigger after dismiss)
- Run axe-core audit as a Vitest step on all pages; fix all critical/serious violations
- Document passing axe audit as a CI gate for new pages

## Phase 11 — Rate Limiting and Audit Logging

**Goal:** Add baseline protection before any production exposure.  
**Depends on:** none (can proceed independently)  
**Priority:** Medium–High (required before production; currently absent on all endpoints including login)

- Add per-IP rate limiting on: `POST /user/login`, `POST /user/token`, `POST /default-api-key/generate`
- Add per-toolkit rate limiting on broker proxy requests
- Add an audit trail for sensitive operations: credential creation/deletion, policy changes, key issuance and revocation
- Store audit events in a new `audit_log` table (toolkit_id, action, resource_id, timestamp)
- Expose `GET /audit` for human admin review
- Add integration tests for rate limit enforcement and audit record creation

## Phase 12 — Toolkit Capability Summary

**Goal:** Provide agents with a prose summary of what a toolkit can currently do.  
**Depends on:** none  
**Priority:** Medium

- Add `GET /toolkits/{id}/summary` returning: which APIs are credentialed, what policy allows, which workflows are accessible, toolkit simulate mode status
- Response must be LLM-consumable (compact, structured prose, no paginated sub-queries required)
- Add unit tests verifying summary content against known toolkit/credential/policy fixtures

---

## Later Phases (Not Yet Planned)

- **OAuth2 first-party setup flow** — `POST /credentials/oauth2/init` → human-facing URL → token grant → auto-refresh; requires design decision on storage and token refresh scheduling
- **Agent-contributed catalog flywheel** — agents submit workflows via `POST /import` private to their toolkit; admin promotes to public; mirrors the auth overlay flywheel pattern
- **Workflow utility tools bundle** — jq-like transform, HTTP utilities, template rendering bundled as pseudo-operations or a sidecar
- **Schema samples endpoint** — `POST /samples` returning example request bodies and response shapes for a given capability, useful for simulate mode grounding
- **HMAC request signing** — for higher-assurance credential binding on APIs that support it
- **Production workflow domain** — canonical hostname for workflow IDs in production deployments (currently `localhost`)
- **Workflow step-level credential injection** — per-step credential overrides for workflows that need different credentials for the same API host in different steps

<!-- Only include items here if they are clearly out of current scope. -->

