# Review Policy

This document defines the review policy for the `ai-review` agent operating on this repository.

## Approval Criteria

Approve a PR when **all** of the following hold:

- CI passes (lint, typecheck, tests).
- No new security vulnerabilities introduced (OWASP top 10).
- Code follows the project's style rules (see [Style Expectations](#style-expectations) below).
- New non-trivial behaviour has test coverage.
- No unnecessary complexity added — changes are minimal and focused.
- Review the openapi specs in `/openapi` and compare to the code (`FastAPI routes`, `documentation`)

## Request Changes Criteria

Request changes when **any** of the following apply:

- CI is failing (lint errors, type errors, test failures).
- Missing tests for non-trivial logic or new code paths.
- Security vulnerabilities (OWASP top 10): injection, auth issues, data exposure, etc.
- Overly broad changes that mix unrelated concerns in a single PR.
- Breaking API changes without a migration path or deprecation notice.
- Code that contradicts the configured ruff/mypy rules (even if it passes due to `type: ignore` or `noqa` without justification).

## Secrets Management

PRs that introduce or modify secrets, credentials, API keys, or security-sensitive configuration
**always require human review** — automated approval is never sufficient for these changes.

The `ai-review` agent must:

1. **Detect** potential secrets — scan diffs for patterns such as API keys, tokens, passwords,
   connection strings, private keys, and `secret`/`credential`/`password` identifiers in
   configuration files, environment variables, OpenAPI `securitySchemes`, and example payloads.
2. **Flag** any matches by adding the `needs-human` label and requesting changes with a comment
   identifying the file(s) and line(s) where secrets-related content was found.
3. **Never approve** a PR that adds, modifies, or references real credential values — even if all
   other approval criteria pass.

Acceptable patterns that do **not** require escalation:
- Placeholder values clearly marked as examples (e.g. `sk_test_EXAMPLE`, `<your-api-key-here>`).
- References to secret names stored in a vault or environment variable (e.g. `${{ secrets.X }}`).
- SecurityScheme definitions in OpenAPI specs that describe *how* auth works without embedding values.

## Escalation Criteria (needs-human)

Add the `needs-human` label and request human review when:

- Architectural changes affecting module boundaries (`broker/`, `control/`, `shared/`).
- New dependency additions with unclear or restrictive licenses (anything other than MIT, Apache-2.0, BSD).
- Changes to CI/CD pipeline configuration (`.github/workflows/`).
- Changes to `.harness/` configuration or agent setup.
- Ambiguous requirements that need product or design input.
- Changes to this file (`REVIEWS.md`) or `CLAUDE.md`.
- **Secrets or credentials detected** in the diff (see Secrets Management above).

## Domain-Specific Rules

Architectural conventions are enforced by the tests in `tests/arch/` and the
scoped rules under `.cursor/rules/`. Key areas to check during review: ORM /
database / schema / repositories, service protocols, the web/HTTP layer,
testing conventions, and the architecture tests themselves.

## Style Expectations

Style is enforced by tooling (`ruff`, `mypy`, `pytest`). See [CLAUDE.md](CLAUDE.md#code-style) for the full configuration. The reviewer should confirm that no `type: ignore` or `noqa` comments are added without justification.
