---
type: constitution
section: tech-stack
generated_by: spec-driven-agent
generated_at: [ISO_TIMESTAMP]
confidence: high
notes: Template example for constitution tech stack
---

# Tech Stack

[PROJECT_NAME] uses the following technology choices based on the current repository state and implementation evidence.

Guidance:
- Prefer facts from code, configs, dependencies, and docs
- Distinguish confirmed facts from inferred choices
- Do not invent technologies not supported by evidence

## Architecture Summary

- **Application style:** [SERVER_SIDE_APP | CLIENT_SERVER_APP | API_SERVICE | CLI | LIBRARY | HYBRID]
- **Primary language(s):** [LANGUAGE_1], [LANGUAGE_2]
- **Rendering model:** [SERVER_RENDERED | SPA | STATIC | API_ONLY | MIXED]
- **Deployment/runtime shape:** [LOCAL_PROCESS | CONTAINER | SERVERLESS | EDGE | UNKNOWN]
- **Current maturity:** [PROTOTYPE | EARLY_STAGE | PRODUCTION | UNKNOWN]

## Core Stack

| Layer | Choice | Evidence / Rationale |
|---|---|---|
| Language | [LANGUAGE] | [evidence or reason] |
| Runtime | [RUNTIME] | [evidence or reason] |
| Main framework | [FRAMEWORK] | [evidence or reason] |
| UI approach | [UI_APPROACH] | [evidence or reason] |
| Styling | [STYLING_APPROACH] | [evidence or reason] |
| Build / packaging | [BUILD_TOOL] | [evidence or reason] |

Add or remove rows based on what is actually present in the repository.

## Key Libraries and Frameworks

- **[LIBRARY_1]** — [role in system]
- **[LIBRARY_2]** — [role in system]
- **[LIBRARY_3]** — [role in system]

## Data and Storage

- **Primary storage:** [DATABASE | FILES | EXTERNAL_SERVICE | NONE]
- **Access pattern:** [ORM | RAW_SQL | QUERY_BUILDER | API | FILESYSTEM]
- **Migrations:** [how schema changes are handled or UNKNOWN]
- **Caching / state:** [if applicable or NONE]
- **Notes:** [constraints or limitations]

## Testing

- **Test framework(s):** [TEST_TOOL]
- **Test types visible:** [UNIT | INTEGRATION | E2E | NONE_OBSERVED]
- **Current testing pattern:** [brief description]

## Tooling and Developer Experience

- **Local development:** [dev server / scripts / watch mode]
- **Build / release:** [build approach]
- **Formatting / linting:** [tools]
- **Type checking:** [tools]
- **CI/CD:** [tooling or NONE_OBSERVED]

## Deployment and Operations

- **Deployment target:** [CLOUD | VM | STATIC_HOST | CONTAINER | UNKNOWN]
- **Environment management:** [ENV_FILES | SECRET_MANAGER | UNKNOWN]
- **Observability:** [LOGGING | METRICS | NONE_OBSERVED]
- **Error handling / resilience:** [brief description]

## Constraints and Conventions

- [IMPORTANT_CONVENTION]
- [ARCHITECTURAL_CONSTRAINT]
- [REPO_OR_TEAM_CONVENTION]
- [DEPENDENCY_OR_ENVIRONMENT_CONSTRAINT]

## What We Are Not Using

- No **[TOOL_OR_PATTERN]** — [reason based on evidence]
- No **[TOOL_OR_PATTERN]** — [reason]

Only include this section if supported by repository evidence.

## Open Questions / Uncertain Areas

- [UNCERTAINTY_1]
- [UNCERTAINTY_2]
- [MISSING_INFORMATION]