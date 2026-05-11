---
name: sdd-new-phase
description: Append a new active phase to specs/roadmap.md. Parses existing phases (active and ✅-completed) to compute the next stable phase number per the lifecycle rule, grounds the proposal against specs/mission.md and specs/tech-stack.md, groups structured questions (goal, dependencies, priority) via AskUserQuestion, then collects a freeform bullet list for the phase body. Edits specs/roadmap.md in place, then invokes the built-in /review skill against the pending change before stopping — committing, pushing, and opening a PR are left to the user. Does not create a feature spec; that is /sdd-new-spec's job.
argument-hint: "[short title or one-sentence intent] (optional)"
---

# /sdd-new-phase — add a new active phase to the roadmap

You are operating within a Spec-Driven Development (SDD) workflow. See `.claude/rules/sdd-constitution.md`.

The **constitution** (mission / tech-stack / roadmap) already exists in `specs/`. This skill adds a fresh active phase — a shippable, independently reviewable, testable vertical slice of work — to `specs/roadmap.md` as a new `## Phase N — Title` block. After writing the edit it invokes the built-in `/review` skill against the pending change, then stops. Branching, committing, and opening a PR are user actions. Once the roadmap change is merged, `/sdd-new-spec <N>` materializes the phase into a feature spec.

## Inputs

Argument in `$ARGUMENTS` (optional):

- empty → prompt the user for a one-sentence description of the phase
- short title or one-sentence intent → used as the starting point for title + goal derivation

## Hard constraints

- **Roadmap-only — zero code changes, zero git actions.** This skill never modifies anything outside `specs/roadmap.md`. It does not run `git`, `gh`, or any commit / branch / push / PR commands. The user handles git themselves after reviewing the edit.
- **Do not renumber existing phases.** Phase numbers are stable identifiers; completed phases stay in the file with a `✅` marker on their heading (per the lifecycle rule in `specs/roadmap.md`). The new phase number is always `max(all existing phase numbers) + 1` — count both active and ✅-completed phases.
- **Do not create a feature spec.** That is `/sdd-new-spec`'s job.
- **Do not touch the `## Later Phases (Not Yet Planned)` section** or the trailing `<!-- Only include items here if they are clearly out of current scope. -->` comment. Active phases and the parking lot are distinct.
- **Do not write to disk before AskUserQuestion completes.** The structured questions lock in decisions that shape the entry; writing early wastes the call.
- **Ground the phase against `specs/mission.md` and `specs/tech-stack.md`.** If the proposal obviously conflicts with the constitution (outside mission scope, violates a tech-stack invariant), stop and surface the conflict before asking the user to lock decisions.
- **`Depends on:` must reference real active phases.** If the user names a dependency, it must match a current `## Phase N — Title` in `specs/roadmap.md` (case-insensitive contains match is fine). Typos get corrected; invented names get rejected.

## Phase 0 — Load context

Load in parallel:

- @specs/mission.md
- @specs/tech-stack.md
- @specs/roadmap.md
- @.claude/rules/sdd-constitution.md

No git state checks — this skill doesn't touch git.

## Phase 1 — Parse roadmap, propose phase identity

Parse `specs/roadmap.md` to extract:

- Every phase block (`## Phase N — Title`, with or without a trailing `✅`): number, title, goal, `Depends on:`, `Priority:`, and a `completed` flag set when the heading ends with `✅`. Ignore the `## Later Phases (Not Yet Planned)` section.
- **Active phases** are those without `✅`; **completed phases** are those with `✅`. The duplicate-overlap check below runs against active phases only — overlapping with already-shipped work is not a conflict.
- **Next phase number**: `max(all phase numbers, active and completed) + 1`. Phase numbers never get reused, so completed phases count toward the ceiling.

If `$ARGUMENTS` is empty, prompt the user for a one-sentence description of what the phase delivers.

**Duplicate-overlap check:** if the proposal obviously overlaps with an existing active phase (strong keyword overlap with a phase title or goal), surface the overlap to the user and ask whether to proceed anyway, merge into the existing phase, or cancel. Do not silently proceed past an apparent duplicate.

**Constitution-conflict check:** reason briefly about whether the proposal fits within the project's mission scope and tech-stack invariants. If there is an obvious conflict (proposes a capability outside the mission; proposes a runtime dependency the tech-stack forbids; violates a load-bearing constraint like the broker-last router rule), surface it and pause. If there is no obvious conflict, proceed silently — do not pad the response with "nothing conflicts" noise.

Derive a candidate **title** in Title Case (e.g. "Local Service Routing", not "local service routing" or "LOCAL SERVICE ROUTING"). Show it to the user alongside the proposed phase number and confirm (or let them override) before Phase 2.

## Phase 2 — AskUserQuestion (MANDATORY, before any disk write)

Issue a single `AskUserQuestion` call containing three grouped questions. Each question offers 3–5 concrete options plus a freeform "other" write-in.

**Question 1 — Goal** (shapes the `**Goal:**` line):
  - Prompt: "One-sentence goal for this phase — what does shipping it mean?"
  - Options: 3–4 goal phrasings derived from the user's initial description, grounded against mission/tech-stack, plus "other (write your own)". Each option is a single sentence starting with an action verb (e.g. "Allow…", "Replace…", "Add…", "Reduce…").

**Question 2 — Dependencies** (shapes the `**Depends on:**` line):
  - Prompt: "Which existing active phase must ship before this one?"
  - Options: "none (self-contained)", each **active** (non-✅) phase title from `specs/roadmap.md` as a separate option, and "other (multiple — specify comma-separated)". Do not offer ✅-completed phases as dependency options — they have already shipped and cannot block new work. If the user picks "other", validate the comma-separated names against active phase titles (case-insensitive contains match). Reject inventions with a one-line correction prompt.

**Question 3 — Priority** (shapes the `**Priority:**` line):
  - Prompt: "What priority level does this phase carry?"
  - Options: `High`, `High (blocker)`, `Medium–High`, `Medium`, plus "other (write your own)". Use the en-dash (`–`, U+2013) in `Medium–High`, not a hyphen — match existing roadmap formatting exactly.
  - The priority legend at the top of `specs/roadmap.md` is the source of truth for what each value means; consult it when the user asks what to pick. In short: `(blocker)` fixes a trust/security gap that makes Mini unsafe for real agent usage **today** (early-access safety bar). Items required for a future production-readiness bar do not need `(blocker)` — Mini is not recommended for production regardless, so state the production rationale in the phase body and pick a normal priority. Other levels express relative queue position.

Only after the user answers all three do you proceed.

## Phase 3 — Collect freeform phase body

Ask the user a single freeform question:

> Now describe the phase body — the concrete bullets that define "shippable". Each bullet should be one change (file, module, route, migration, test, doc, etc.). Freeform; I'll format them.

Parse their response into bullets (one per line, `- ` prefix). Do not invent bullets; keep only what the user wrote. Light formatting is fine (normalize leading dashes, capitalization, trailing punctuation); content changes are not.

If the response is fewer than three bullets, ask once: "A phase usually lists at least three concrete tasks — anything to add, or is this intentionally small?" Accept a short phase if the user confirms.

If the user clearly typed a paragraph of prose rather than bullets, split it into a short **context paragraph** (kept as-is before the bullet list) and ask them for the concrete bullets. A phase may have both a context paragraph and a bullet list — see any active phase in `specs/roadmap.md` with prose between the `**Priority:**` line and the bullets for the shape.

## Phase 4 — Edit the roadmap

Edit `specs/roadmap.md` to insert the new phase. **Insertion rules:**

- Phase blocks (active and ✅-completed alike) are separated from the `## Later Phases (Not Yet Planned)` section by a `---` horizontal rule.
- Insert the new block **immediately before the `---` that precedes `## Later Phases`** — after the last existing phase block, regardless of whether the trailing phase is active or completed. Phase numbers are sequential by number, not by status.
- Separate the new block from the previous phase with a single blank line; match the existing file's spacing.
- Do not renumber any existing phase. Do not strip `✅` markers from completed phases.
- Do not edit the `## Later Phases (Not Yet Planned)` section or the trailing HTML comment.

**Block format** — match existing phases exactly:

```
## Phase <N> — <Title>

**Goal:** <goal sentence ending with a period>.
**Depends on:** <none (self-contained) | comma-separated phase titles, optional parenthetical rationale>
**Priority:** <priority, optional parenthetical rationale>

<optional 1–3 sentence context paragraph — include only if the user provided prose alongside bullets>

- <bullet 1>
- <bullet 2>
- <bullet 3>
```

If `Depends on:` is `none`, follow an existing example like `none (self-contained broker change)` when the user provided a one-line reason; bare `none` is also fine. Do not invent a rationale.

## Phase 5 — Review the edit

Immediately after the `specs/roadmap.md` edit lands, invoke the built-in `review` skill via the `Skill` tool with argument `local changes`. The `review` skill handles a working-tree diff when given that argument — treat it as a normal capability of the skill.

- Invoke the `Skill` tool with `skill: "review"` and `args: "local changes"`.
- Do not skip or defer this step; it is part of the skill's contract.
- Do **not** narrate the invocation mechanism, describe the skill as PR-oriented, explain arguments, or frame the call as a workaround. Just run it and report its findings.
- Surface the reviewer's findings verbatim in your response; do not summarize them away.
- If the reviewer flags issues that are clearly in-scope for this skill (e.g. a malformed phase block, a broken `Depends on:` reference, wrong phase number), offer to apply a fix and ask the user to confirm before re-editing. Do not auto-apply fixes.
- If the `Skill` invocation itself fails (tool error, unrecognized arg, unreachable), surface the error to the user and proceed to Phase 6; do not silently drop the step, and do not retry more than once.

## Phase 6 — Report back

Return to the user in a few lines:

- Phase number and title that were added
- File edited: `specs/roadmap.md`
- **Review outcome:** a one-line verdict from Phase 5 — `clean` (no blockers, no suggestions), `suggestions available` (reviewer offered optional improvements), or `blocker` (reviewer flagged an in-scope issue that should be fixed before commit). If Phase 5's invocation failed, say so here instead (`review skipped — <one-line error>`).
- **Actionable suggestions from the review** (only if the outcome was `suggestions available` or `blocker`): a short bulleted list of the concrete fix offers Phase 5 surfaced, each a single line the user can accept or decline. Do not repeat the full review body — it was already printed verbatim in Phase 5.
- Next steps (user-driven — this skill does not do them):
  1. Review the diff (`git diff specs/roadmap.md`).
  2. Branch + commit + PR per `.claude/rules/git-workflow.md` and `.claude/rules/conventional-commits.md` (suggested header: `docs(roadmap): add phase <N> — <short-slug>`).
  3. Once merged, run `/sdd-new-spec <N>` to materialize the phase into a feature spec.