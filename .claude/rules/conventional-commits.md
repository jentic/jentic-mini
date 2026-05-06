Commit messages MUST follow Conventional Commits (https://www.conventionalcommits.org/en/v1.0.0/).

Format: `type(scope): description` — max 69 characters in the header.

- Types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `perf`, `build`, `ci`, `style`, `revert`
- `feat` / `fix` apply only to changes an end user sees. Developer tooling (agent harness configs, editor configs, dev scripts, dependency bumps) uses `chore`. Litmus test: does an end user of Jentic Mini see this change? If no, it's `chore`.
- Scope: always include a scope. Use the primary subject of the change:
  - For `docs`: the doc file name without extension (e.g. `docs(DEVELOPMENT)`, `docs(README)`, `docs(TESTING)`)
  - For `ci`: the workflow/config file name without extension (e.g. `ci(ci-backend)`, `ci(docker-publish)`, `ci(release)`). When the change IS the CI config, use type `ci` — not `chore(ci)`.
  - For code: the module, router, or component name (e.g. `fix(broker)`, `feat(search)`, `refactor(ui)`)
  - For `chore`: prefer harness-agnostic scopes — `chore(harness)` covers anything under `.claude/`, `.cursor/`, `.codex/`, etc.
- Description: lowercase, imperative mood, no trailing period