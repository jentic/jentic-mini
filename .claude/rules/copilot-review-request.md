After creating a PR with `gh pr create`, request a Copilot code review and wait for it in the background — don't block other work. Skip this for draft PRs; Copilot won't review until they're marked ready.

Flow:

1. `gh pr edit <N> --add-reviewer Copilot` (assignment slug is `Copilot`; the bot later posts comments under `copilot-pull-request-reviewer[bot]`). If the call fails (Copilot review not enabled for the repo/org, missing entitlement), continue silently — the PR ships without it.
2. Kick off a background wait with `Bash` + `run_in_background: true`. Poll `gh api repos/<OWNER>/<REPO>/pulls/<N>/reviews` every ~60s for an entry whose `user.login` starts with `copilot-pull-request-reviewer`, with a hard cap (e.g. 10 minutes). The harness notifies you when the loop exits — don't foreground-poll.
3. On the notification, fetch the review, summarize it for the user (which comments look actionable, which don't), and ask whether to address it. If yes, follow `copilot-review-comments.md` — fix, push, then resolve the threads the push addressed. If no, stop.
4. If the cap elapses without a review, tell the user instead of going quiet.

Pair with `copilot-review-comments.md`: this rule handles the request + wait, that one handles the response.
