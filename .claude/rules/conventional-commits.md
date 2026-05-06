Commit messages MUST follow Conventional Commits (https://www.conventionalcommits.org/en/v1.0.0/).

Format: `type(scope): description` — max 69 characters in the header.

- Types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `perf`, `build`, `ci`, `style`, `revert`
- `feat` / `fix` apply only to the **product** — code under `src/`, `ui/`, `alembic/`, or anything that ships to users. Tooling around the product (developer ergonomics, IDE/editor configs, agent harness configs, lint/format setup, scripts) uses `chore`. Examples:
  - Adding or changing anything under `.claude/`, `.cursor/`, `.codex/`, or any agent harness config → `chore(harness)`. Not `feat`.
  - Adding a pre-commit config or husky hook → `chore(hooks)`.
  - Updating editor configs (`.editorconfig`, `.vscode/`) → `chore(editor)`.
  - Adding a developer script under `scripts/` that no end user runs → `chore(scripts)`.
  - Bumping a dependency → `chore(deps)`.
  - The litmus test: does an end user of Jentic Mini see this change? If no, it's `chore`.
- Scope: always include a scope. Use the primary subject of the change:
  - For `docs`: the doc file name without extension (e.g. `docs(DEVELOPMENT)`, `docs(README)`, `docs(TESTING)`)
  - For `ci`: the workflow/config file name without extension (e.g. `ci(ci-backend)`, `ci(docker-publish)`, `ci(release)`). When the change IS the CI config, use type `ci` — not `chore(ci)`.
  - For code: the module, router, or component name (e.g. `fix(broker)`, `feat(search)`, `refactor(ui)`)
  - For `chore`: the subsystem, harness-agnostic where possible (`harness`, `hooks`, `editor`, `scripts`, `deps`).
- Description: lowercase, imperative mood, no trailing period