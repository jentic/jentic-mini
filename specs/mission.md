---
type: constitution
section: mission
generated_by: spec-driven-agent
generated_at: 2026-04-23T00:00:00Z
confidence: high
---

# Mission

Jentic Mini exists because building AI agents that call real-world APIs is painful and unsafe.
Developers end up hardcoding credentials in prompts, writing bespoke auth glue for every service,
and risking credential leakage every time an agent is given a new capability.

The core insight is that credentials should never touch the agent. An execution layer should sit
between the agent and the outside world, injecting credentials at request time, enforcing scoped
access policies, and giving humans control over what agents can do — without slowing the agent down.

## What We Do

Jentic Mini is a self-hosted API execution middleware for AI agents, and a credential-aware broker
for any caller that can reach its HTTP surface (including developer CLIs via the broker-CLI pattern).

We:
- **Search** — let agents find the right API operation or workflow from a catalog of 10,000+ APIs using natural language (BM25 full-text search)
- **Broker** — transparently proxy authenticated requests to upstream APIs, injecting credentials at runtime so agents never see or handle secrets
- **Orchestrate** — execute multi-step Arazzo workflows, routing each step through the broker for consistent credential injection, policy enforcement, and tracing
- **Govern** — enforce per-toolkit access policies (allow/deny rules), per-key IP restrictions, and human-in-the-loop permission escalation
- **Observe** — record execution traces at the operation and workflow-step level for audit and debugging
- **Learn** — accumulate structured notes (auth quirks, usage hints, corrections) contributed by agents against operations and workflows, improving canonical specs over time

## Guiding Principle

**Humans spend as little time in the UI as possible.** The agent tells the user when something
needs their attention and gives them a single link — the UI just needs to be the right landing
page for that action. Secondary functions (browsing APIs, reviewing traces, auditing toolkit
access) still need to work adequately, but agents should increasingly handle those on the
human's behalf too.

## Core Invariants

These invariants are load-bearing: every future feature must preserve them.

- **Secrets never touch the agent.** Credential values are encrypted on write, never returned by the API, and injected by the broker at request time. Losing the vault key (`JENTIC_VAULT_KEY`) means losing access to every stored credential — there is no recovery path.
- **Two-actor authentication.** Humans authenticate with bcrypt passwords and httpOnly JWT cookies; agents authenticate with `X-Jentic-API-Key: tk_xxx` bound to a toolkit. There is no admin API key and no superuser env var; `docker exec` is the only superuser path. A compromised agent key cannot self-escalate.
- **Capability ID format is an API contract.** `METHOD/host/path` (e.g. `GET/api.stripe.com/v1/customers`). Agents persist these IDs, so the shape must remain stable across versions and editions.
- **Alembic migrations are the schema source of truth**, not code. They run automatically at container startup.
- **The broker catch-all route must be registered last.** Violating this silently swallows internal routes.

## Who We Serve

- **AI developers and hobbyists** — individuals building agents that need access to external APIs without managing per-service auth in code or prompts
- **Small teams** — groups who want self-hosted control over their agent infrastructure, credential storage, and access policies
- **Agent frameworks and tools** — systems (e.g. OpenClaw) that integrate Jentic Mini as a skill layer for their agents
- **Human admins** — operators who approve permission requests, manage credentials, and audit agent activity via the admin UI
- **Developers using the broker CLI** — humans who route CLI tools (git, curl, stripe, etc.) through the broker to get the same credential injection and tracing without embedding secrets locally

## Target Audience

- **Self-hosters** — users who want full control over their data and credentials without sending them to a cloud service
- **Security-conscious teams** — builders who need an auditable, single-chokepoint credential injection model rather than per-agent secret management
- **Open-source Jentic ecosystem adopters** — users of the Jentic platform who want a compatible self-hosted option (Jentic Mini is API-compatible with Jentic hosted/VPC editions)

## What Success Looks Like

- An agent can discover, call, and orchestrate real-world APIs using only a single toolkit key — never touching any credential value
- A human can set up the system, add credentials, and grant access to an agent in under 15 minutes with no code changes
- A security incident (compromised agent key) can be isolated by revoking that key without affecting other agents or credentials
- When an agent needs access it doesn't have, it can request it and a human can approve it via a single URL — the agent continues without human involvement for everything else
- All agent API calls are traceable, auditable, and explainable at the step level
- Agent-contributed notes (auth quirks, usage hints, corrections) flow back into shared specs, so the catalog improves without manual curation

## Privacy & Telemetry

- Anonymous install telemetry reports an install UUID and version at startup; opt-out is a single env var (`JENTIC_TELEMETRY=off`).
- No credential values, toolkit data, or execution payloads leave the host.
- All credential storage is local SQLite + Fernet encryption; the vault key lives next to the database and is owned by the container's non-root user.

## Current State

Jentic Mini is in **early access** (v0.9.0) and under active development. It is not recommended for
production use. Known risks include incomplete backend unit test coverage (integration and contract
tests exist; module-level unit tests are a gap), no rate limiting on any endpoint including login,
no audit trail for sensitive operations, and some security gaps that have not yet been identified.
It is designed for personal, development, and evaluation environments.

## Assumptions & Unknowns

- *Inferred*: The primary growth driver is the Jentic public API catalog (10,000+ specs); the more APIs are auto-imported and workflow-ready, the more useful the system becomes immediately
- *Inferred*: Agent-contributed notes and overlays form a feedback loop that improves the shared catalog, mirroring the auth overlay flywheel
- *Unknown*: Long-term intended user for production workloads (current guidance explicitly defers production use)
- *Unknown*: Whether Jentic Mini will eventually converge feature parity with the hosted edition or remain deliberately simpler
