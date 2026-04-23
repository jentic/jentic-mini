Commit messages MUST follow Conventional Commits (https://www.conventionalcommits.org/en/v1.0.0/).

Format: `type(scope): description` — max 69 characters in the header.

- Types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `perf`, `build`, `ci`, `style`, `revert`
- Scope: package short name without `apidom-` prefix (e.g. `core`, `ns-overlay-1`, `reference`, `traverse`)
- Description: lowercase, imperative mood, no trailing period
- Enforced by husky commit-msg hook via commitlint — fix the message, never bypass the hook