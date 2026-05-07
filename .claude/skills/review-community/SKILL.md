---
name: review-community
description: Review a pull request authored by someone other than the current GitHub user, applying the team's diplomatic review-comments tone. Use when the PR author's GitHub login differs from the current user's `gh api user` login. For own PRs, use the built-in /review directly. Detects authorship automatically and refuses on self-authored PRs.
argument-hint: "[pr-number | pr-url] (optional — defaults to the PR for the current branch)"
---

# /review-community — review someone else's PR with the community tone

This skill wraps the built-in `/review` command with two additions:

1. **Authorship guard** — refuses to run if the PR author's GitHub login matches the current user's. For self-reviews, use `/review` directly with its default voice.
2. **Tone injection** — inlines the diplomatic review-comments style into this turn so the tone applies without flipping the session output style. Activating the style via `/config` → Output style would replace Claude Code's default software-engineering system prompt; this skill avoids that by overlaying the tone on top of the default.

## Tone for this review

The tone, structure, and constraints below are the source of truth for
voice and feedback structure. Follow them for every comment drafted in
this review.

!`cat .claude/output-styles/review-comments.md`

## Phase 0 — Resolve PR and verify authorship

Run this once and use the values for the rest of the skill. `set -e`
ensures any failed command stops the block; if it stops, surface the
error to the user and do not proceed.

```bash
set -e

if [ -n "$ARGUMENTS" ]; then
  PR="$ARGUMENTS"
else
  PR=$(gh pr view --json number -q .number)
fi

PR_AUTHOR=$(gh pr view "$PR" --json author -q .author.login)
GH_USER=$(gh api user -q .login)

echo "PR=$PR"
echo "PR_AUTHOR=$PR_AUTHOR"
echo "GH_USER=$GH_USER"
```

Expected outcomes:

- **`gh pr view` with no argument fails** (no PR for current branch) →
  stop and ask the user for a PR number or URL. Don't guess.
- **`gh api user` fails or returns empty `$GH_USER`** → stop. The
  authorship guard cannot run without a confirmed login. Tell the user
  to authenticate (`gh auth status`) and try again.
- **`$PR_AUTHOR` equals `$GH_USER`** → stop. Tell the user this is
  their own PR and to use `/review` directly. Do not proceed.
- **`$PR_AUTHOR` differs from `$GH_USER`** → continue. State who
  authored the PR before starting the review, so the user has
  confirmation the guard saw the right author.

## Phase 1 — Run the review

Invoke the built-in `/review` skill against `$PR` via the Skill tool.
The tone instructions inlined in "Tone for this review" above apply to
all comments drafted in this turn.

If the user asks follow-up questions in subsequent turns ("expand
point 3," "draft the GitHub comment for line 42"), the inlined tone
instructions will not carry over automatically. Re-read the style file
when needed. A session-level voice lock is possible via `/config` →
Output style → review-comments, but it replaces Claude Code's default
software-engineering system prompt — not recommended unless the whole
session is review work.

## Out of scope

Severity grouping, technical depth, and what gets flagged remain
whatever the built-in `/review` does — this skill only adds the
authorship guard and the tone overlay.
