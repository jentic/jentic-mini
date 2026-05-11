`/review` and `/security-review` always produce comments — that's the audit trail. Additionally, for each mechanical finding that remains clearly correct after re-reading the surrounding code in its current state, push a follow-up commit on the same PR (per `git-workflow.md` / `conventional-commits.md`) and, if the finding lived as a PR review thread, resolve it per `copilot-review-comments.md`.

The re-check is per-finding: re-open the file(s) the finding points at, confirm the issue still applies (code may have shifted since the review was generated), and confirm the fix has no logic implications. If any of those is uncertain, leave it as a comment only.

The comment is the record; the commit just closes the loop without bouncing through the user.

If the follow-up commit breaks tests or hooks, revert it and convert the finding back to a comment — don't fix forward with more commits.

### Follow-up commit only when *all* hold

- PR author matches the harness user — verify with `gh pr view <num> --json author -q .author.login` against `gh api user -q .login`. Community PRs are review-only (`review-community` never pushes to a contributor's branch).
- Fix is mechanical: lint, typo, dead import, missing type, formatting, narrow null-check.
- No logic change. Judgment calls stay comment-only.
- Single-concern, small enough to verify at a glance.

