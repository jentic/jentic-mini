---
name: sdd-distill-lessons
description: Distil per-spec retrospectives into specs/lessons.md so future spec authoring absorbs the learning. Reads specs/*/retrospective.md, groups recurring patterns, surfaces candidate lessons and tech-stack.md promotion candidates via AskUserQuestion, writes confirmed additions to specs/lessons.md, then invokes /review against the pending change before stopping. Never edits specs/tech-stack.md — promotion candidates are surfaced for the user to hand-promote. Never runs git, gh, or any commit/branch/PR commands.
argument-hint: "(no arguments)"
---

# /sdd-distill-lessons — distil retrospectives into specs/lessons.md

You are operating within a Spec-Driven Development (SDD) workflow. See `.claude/rules/sdd-constitution.md`.

This skill is the manual roll-up step of the SDD feedback loop. Per-spec `specs/<date>-<slug>/retrospective.md` files capture what individual specs missed; this skill reads them, deduplicates lessons across retrospectives, and writes the durable additions into `specs/lessons.md` so `/sdd-new-spec` and `/sdd-new-phase` consume them on their next run. When a lesson recurs across multiple retrospectives **and** clearly names a load-bearing invariant, the skill flags it as a `specs/tech-stack.md` promotion candidate for the user to hand-promote.

## Hard constraints

- **`specs/lessons.md` only — no other writes.** This skill edits exactly one file. `specs/tech-stack.md` promotions are surfaced as user-actionable suggestions; the skill never edits `tech-stack.md`. Retrospectives are read-only.
- **Do not write to disk before the AskUserQuestion confirmation completes.** The grouped lesson candidates exist to lock in what gets captured; writing early wastes the call.
- **No git actions.** This skill writes files and stops. Branching, committing, and PR creation are user actions per `.claude/rules/git-workflow.md`.
- **Ground every proposed lesson in at least one retrospective.** Do not invent lessons; do not paraphrase a retrospective into a lesson it does not actually support.
- **Dedupe before proposing.** If two retrospectives surface the same lesson (semantically), group them into one candidate referencing both retrospectives — do not propose duplicate bullets.
- **Do not re-propose already-captured lessons.** Compare each candidate against the existing `specs/lessons.md` body and skip anything substantively present.

## Phase 0 — Load context

Load in parallel:

- @specs/mission.md
- @specs/tech-stack.md
- @specs/lessons.md
- @.claude/rules/sdd-constitution.md

Enumerate `specs/*/retrospective.md` files (every dated feature-spec directory may or may not have one — retrospectives are optional). Load each in parallel via `Read`.

If no retrospectives exist, stop with a one-line summary ("No retrospectives found under `specs/*/retrospective.md`; nothing to distil.") — there is nothing to do.

## Phase 1 — Parse retrospectives and existing lessons

For each retrospective, extract:

- Phase number and title from the H1
- Each bullet under `## Lesson for future specs`
- The `## Promotion candidate` verdict (`yes` or `no` plus the rationale sentence)

For `specs/lessons.md`, extract the bullets currently present under `## Lessons` (the section may still contain the initialisation placeholder `_(empty — …)_` — treat that as no lessons captured yet).

## Phase 2 — Group and dedupe candidate lessons

Combine all extracted lesson bullets from all retrospectives. Group lessons that say the same thing semantically (different phrasings of the same guidance count as one). For each grouped candidate:

- Record the source retrospectives (one or more file paths)
- Phrase the candidate as a single actionable bullet
- Mark as a **promotion candidate** if **either** (a) two or more retrospectives surfaced this same lesson, **or** (b) any source retrospective marked `## Promotion candidate: yes`. Promotion is a strong signal — only flag when at least one of those criteria is met.
- Skip candidates that already appear (substantively) in `specs/lessons.md`'s existing bullet list

If after deduplication there are zero new candidates, stop with a one-line summary ("All retrospective lessons are already captured in `specs/lessons.md`; nothing to add.") — still report any **promotion candidates** identified (those can apply even when nothing new is being added to `lessons.md`, if a lesson already in `lessons.md` has now recurred across enough retros).

## Phase 3 — AskUserQuestion (MANDATORY, before any disk write)

Issue a single `AskUserQuestion` call (multi-select) listing the candidate lessons as options:

- Prompt: "Which lessons should I add to `specs/lessons.md`?"
- Header: `Lessons` (≤ 12 chars per the schema)
- `multiSelect: true`
- Per the schema, **at most 4 options per call**. If there are more than 4 candidates, present the 4 with the strongest signal first (highest source-retrospective count; ties broken by oldest retrospective first), and note in the response that remaining candidates can be reviewed on a follow-up run. Each option:
  - `label`: short version of the lesson (≤ ~40 chars; truncate with `…` if needed)
  - `description`: the full lesson bullet + ` (sources: <retro-1-path>[, <retro-2-path> …])` + ` [promotion candidate]` when applicable

The automatic freeform write-in lets the user re-phrase a candidate before accepting or describe why they want to skip one.

## Phase 4 — Edit specs/lessons.md

For each lesson the user confirmed in Phase 3, append a bullet under the `## Lessons` section of `specs/lessons.md`. Bullet shape:

```
- <lesson text> — captured from `specs/<date>-<slug>/retrospective.md`[, `specs/<other-date>-<other-slug>/retrospective.md`]
```

If `## Lessons` still contains the initialisation placeholder (`_(empty — …)_`), replace the placeholder with the new bullets. Otherwise, append after the existing bullets.

Do not edit any section of the file other than `## Lessons`. Do not touch `## Lifecycle` or the file's header.

## Phase 5 — Surface promotion candidates

For each candidate flagged as a promotion candidate in Phase 2 (whether or not the user accepted it in Phase 3 — promotion is about recurrence, not about whether the lesson belongs in `lessons.md`), report it to the user as a `specs/tech-stack.md` promotion suggestion. **Do not edit `tech-stack.md`** — surface only.

Format:

```
Promotion candidates for `specs/tech-stack.md` (manual edits):

- <lesson text> — recurring across <N> retrospectives (<retro-1-path>, <retro-2-path>, …). Suggested home: `specs/tech-stack.md` <section if obvious, e.g. "## Conventions" or "## Constraints">.
```

If no candidates qualify, omit this section.

## Phase 6 — Review the edit

Immediately after the `specs/lessons.md` edit lands, invoke the built-in `review` skill via the `Skill` tool with argument `local changes`. The `review` skill handles a working-tree diff when given that argument — treat it as a normal capability of the skill.

- Invoke the `Skill` tool with `skill: "review"` and `args: "local changes"`.
- Do not skip or defer this step; it is part of the skill's contract.
- Do **not** narrate the invocation mechanism, describe the skill as PR-oriented, explain arguments, or frame the call as a workaround. Just run it and report its findings.
- Surface the reviewer's findings verbatim; do not summarise them away.
- If the reviewer flags an in-scope issue (e.g. a malformed bullet, a wrong source reference, a stale placeholder left behind), offer to apply a fix and ask the user to confirm before re-editing. Do not auto-apply fixes.
- If the `Skill` invocation itself fails (tool error, unrecognised arg, unreachable), surface the error and proceed to Phase 7; do not silently drop the step, and do not retry more than once.

## Phase 7 — Report back

Return to the user in a few lines:

- Number of retrospectives read
- Lessons added to `specs/lessons.md` (count + one bullet per accepted lesson)
- Lessons skipped (count + one-line reason: already captured / user declined / queued for follow-up run)
- Promotion candidates surfaced for manual `specs/tech-stack.md` addition (count + one bullet per, with source retros)
- **Review outcome:** one-line verdict from Phase 6 — `clean`, `suggestions available`, `blocker`, or `review skipped — <one-line error>`
- Next steps (user-driven — this skill does not do them):
  1. Review the diff (`git diff specs/lessons.md`).
  2. Hand-promote any flagged candidates into `specs/tech-stack.md` if appropriate.
  3. Branch + commit + PR per `.claude/rules/git-workflow.md` and `.claude/rules/conventional-commits.md` (suggested header: `docs(lessons): distil retrospectives`).
