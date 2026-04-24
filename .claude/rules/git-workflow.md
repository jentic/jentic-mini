## Branches

- Prefix branches by change type: `feature/`, `fix/`, `chore/`, `docs/`, `test/`.
- After the slash, use a short kebab-case description: `fix/fix-everything-that-was-broken`.
- If an issue exists for the work, put the issue number right after the slash: `fix/1234-fix-all-the-other-things`.

## Commits

- Break work into **atomic** logical units — each commit should stand on its own and be reviewable in isolation.
- Reference related issues with `Refs #<issue>` in the commit body.
- Do NOT use GitHub magic close-keywords (`Closes`, `Fixes`, `Resolves`) in commit messages — those belong in the PR body so they close issues on merge, not on every push.
- Sign off every commit per the Developer Certificate of Origin: `git commit -s` (adds a `Signed-off-by:` trailer).

## Pull requests

- Keep PRs **small and focused**. Split unrelated changes into separate PRs.
- Magic close-keywords (`Closes #123`, `Fixes #123`) go in the PR **body**, not the title.
- PRs are **squash-merged**. The squash commit message must follow Conventional Commits (see `conventional-commits.md`).
- When a PR adds or changes a feature, update the relevant documentation in the same PR.