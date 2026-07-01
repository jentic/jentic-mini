# RepoStandardsAgent — steering notes

Additional, job-only context for the repo-standards maintenance job. Layered
**additively** on top of `CLAUDE.md` / `AGENTS.md` (those win on conflict).

## What the repo's own tooling already covers (do NOT re-flag)

- Import ordering, unused imports, unused locals, formatting, type-hint presence
  → ruff + mypy strict (`make lint`).
- Architectural conventions are enforced by `tests/arch/*` (128 tests, all green
  as of 2026-06-29). Notable ones: layered Router→Service→Repository
  (`test_no_direct_db`, `test_web_layer`), metrics/tracing/crypto facades,
  no stdlib logging, no manual commits, commit-message convention, OpenAPI
  conformance. If an arch test exists for a rule, trust it — don't hand-audit.

## Detection assets

None yet. (No new lint configs or check scripts created — the existing arch-test
suite is the detection mechanism for convention drift.)
