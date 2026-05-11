`/review` and `/security-review` always produce comments — that's the audit trail. For findings that pass the re-check (below), push a follow-up commit on the same PR (per `git-workflow.md` / `conventional-commits.md`). When auto-applying a bug fix, append an `## Auto-applied fixes` section to the PR review comment (or post a new comment if none exists). If the finding lived in a PR review thread, resolve it per `copilot-review-comments.md`.

The re-check is per-finding: re-open the file(s) the finding points at, confirm the issue still applies against current code, and confirm the fix fits the categories below. If uncertain, leave it as a comment directed to the PR author.

If the follow-up commit breaks tests or hooks, revert it and convert the finding back to a comment — don't fix forward with more commits.

### Follow-up commit when *all* hold

- PR author is a jentic org member — verify with `gh api orgs/jentic/members/<author_login>` (204 = member, 404 = not). Non-member PRs are review-only; use `review-community`, which never pushes to a contributor's branch.
- The finding is one of:
  - **Mechanical**: lint, typo, dead import, missing type, formatting, narrow null-check.
  - **Bug introduced by this PR**: a regression the PR's own diff caused, identifiable against the base branch.
- No architectural or design change — those go to the PR author as a comment regardless of authorship.
- Single-concern, small enough to verify at a glance.
