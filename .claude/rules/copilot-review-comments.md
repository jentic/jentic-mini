After pushing fixes for Copilot review comments, resolve the threads automatically — don't wait to be asked. Only resolve threads whose feedback the pushed commit actually addresses; skip the rest.

Flow (via `gh api graphql`):

1. Query `reviewThreads` on the PR.
2. Filter to `isResolved=false` where the first comment's author is `copilot-pull-request-reviewer`.
3. For each thread, decide whether the pushed commit addresses it. If not, skip.
4. Reply with `addPullRequestReviewThreadReply` — `Addressed by <pushed-sha>`.
5. Call `resolveReviewThread`.

The reply is the audit trail, so the resolution isn't mistaken for a dismissal.
