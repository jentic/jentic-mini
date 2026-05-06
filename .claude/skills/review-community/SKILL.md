---
name: review-community
description: Review a pull request authored by someone other than the current git user, applying the team's diplomatic review-comments tone. Use when the PR author differs from `git config user.name` — for own PRs, use the built-in `/review` directly. Detects authorship automatically; refuses to run on self-authored PRs.
argument-hint: "[pr-number | pr-url] (optional — defaults to the PR for the current branch)"
---

# /review-community — review someone else's PR with the community tone

This skill wraps the built-in `/review` command with two additions:

1. **Authorship guard** — refuses to run if the PR author matches the current git user. For self-reviews, use `/review` directly with its default voice.
2. **Tone injection** — applies the diplomatic review-comments style for this turn, so feedback respects the author's effort.

## Tone for this review

Apply the tone, structure, and constraints defined in:

@.claude/output-styles/review-comments.md

That file is the source of truth for voice and feedback structure. Follow
it for every comment drafted in this review.

## Phase 0 — Resolve the PR

Argument in `$ARGUMENTS` (optional):

- empty → use the PR associated with the current branch
- integer or URL → use that PR

Resolve the PR number once and reuse it:

```bash
PR="${ARGUMENTS:-}"
if [ -z "$PR" ]; then
  PR=$(gh pr view --json number -q .number)
fi
```

If `gh pr view` fails with no argument (no PR for the current branch), stop
and ask the user for a PR number or URL. Don't guess.

## Phase 1 — Authorship check

```bash
PR_AUTHOR=$(gh pr view "$PR" --json author -q .author.login)
GIT_USER=$(git config user.name)
GH_USER=$(gh api user -q .login 2>/dev/null)
```

The PR author is a GitHub login. Compare against `$GH_USER` (also a GitHub
login) — that's the reliable match. `$GIT_USER` is a display name and may
not match the login; use it only as a fallback.

**If `$PR_AUTHOR` equals `$GH_USER`:** stop. Tell the user this is their
own PR and to use `/review` directly. Do not proceed.

**If they differ:** continue. Briefly state who authored the PR before
starting the review, so the user has confirmation the guard saw the right
author.

## Phase 2 — Run the review

Invoke the built-in `/review` skill against `$PR`. The tone instructions
inlined above apply to all comments drafted in this turn.

If the user asks follow-up questions in subsequent turns ("expand point
3," "draft the actual GitHub comment for line 42"), the inlined tone
instructions will not carry over automatically — re-read
`.claude/output-styles/review-comments.md` if needed, or remind the user
they can `/output-style review-comments` for a full-session voice lock.

## What this skill does NOT do

- Post comments to GitHub. `/review` produces the review; posting is a
  separate explicit step.
- Switch the session output style. That requires `/output-style
  review-comments` typed by the user — skills cannot run harness commands.
- Override `/review`'s own behavior beyond tone. Severity grouping,
  technical depth, and what gets flagged remain whatever `/review` does.
