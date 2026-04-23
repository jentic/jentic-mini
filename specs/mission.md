---
type: constitution
section: mission
generated_by: spec-driven-agent
generated_at: 2026-04-23T00:00:00Z
sources:
  - @README.md
  - @docs/ARCHITECTURE.md
  - @docs/ROADMAP.md
  - @src/main.py
  - @AGENTS.md
  - @.claude/templates/sdd/constitution/mission.example.md
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

Jentic Mini is a self-hosted API execution middleware for AI agents.

We:
- **Search** — let agents find the right API operation or workflow from a catalog of 10,000+ APIs using natural language (BM25 full-text search)
- **Broker** — transparently proxy authenticated requests to upstream APIs, injecting credentials at runtime so agents never see or handle secrets
- **Orchestrate** — execute multi-step Arazzo workflows, routing each step through the broker for consistent credential injection, policy enforcement, and tracing
- **Govern** — enforce per-toolkit access policies (allow/deny rules), per-key IP restrictions, and human-in-the-loop permission escalation
- **Observe** — record execution traces at the operation and workflow-step level for audit and debugging

## Who We Serve

- **AI developers and hobbyists** — individuals building agents that need access to external APIs without managing per-service auth in code or prompts
- **Small teams** — groups who want self-hosted control over their agent infrastructure, credential storage, and access policies
- **Agent frameworks and tools** — systems (e.g. OpenClaw) that integrate Jentic Mini as a skill layer for their agents
- **Human admins** — operators who approve permission requests, manage credentials, and audit agent activity via the admin UI

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

## Current State

Jentic Mini is in **early access** (v0.9.0) and under active development. It is not recommended for production use. 
Known risks include incomplete test coverage, no rate limiting, no audit trail for sensitive operations, 
and some security gaps that have not yet been identified. It is designed for personal, development, and evaluation environments.

## Assumptions & Unknowns

- *Inferred*: The primary growth driver is the Jentic public API catalog (10,000+ specs); the more APIs are auto-imported and workflow-ready, the more useful the system becomes immediately
- *Unknown*: Long-term intended user for production workloads (current guidance explicitly defers production use)
- *Unknown*: Whether Jentic Mini will eventually converge feature parity with the hosted edition or remain deliberately simpler

