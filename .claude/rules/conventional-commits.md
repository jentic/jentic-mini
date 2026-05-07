Commit messages MUST follow Conventional Commits (https://www.conventionalcommits.org/en/v1.0.0/).

*Enforced by `.husky/commit-msg` (commitlint, config: `ui/.commitlintrc.json`) and a Claude PreToolUse hook (`.claude/hooks/commitlint-before-commit.py`) that runs the same check before `git commit` is fired.*

Format: `type(scope): description` — max 69 characters in the header.

- Types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `perf`, `build`, `ci`, `style`, `revert`
- If a change ships to users, it's `feat` (new capability) or `fix`
  (bug). Internal developer tooling (agent harness configs, editor
  configs, dev scripts, dependency bumps) uses `chore`. The other
  types (`refactor`, `test`, `docs`, `perf`, `build`, `ci`, `style`,
  `revert`) take precedence over `chore` when they fit.
- Scope: always include a scope. Use the primary subject of the change:
  - For `docs`: the doc file name without extension (e.g. `docs(DEVELOPMENT)`, `docs(README)`, `docs(TESTING)`)
  - For `ci`: the workflow/config file name without extension (e.g. `ci(ci-backend)`, `ci(docker-publish)`, `ci(release)`). When the change IS the CI config, use type `ci` — not `chore(ci)`.
  - For code: the module, router, or component name (e.g. `fix(broker)`, `feat(search)`, `refactor(ui)`)
  - For `chore`: prefer harness-agnostic scopes — `chore(harness)`
    covers anything under `.claude/`, `.cursor/`, `.codex/`, etc.
- Description: lowercase, imperative mood, no trailing period
