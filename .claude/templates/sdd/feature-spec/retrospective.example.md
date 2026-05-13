# Phase [PHASE_NUMBER] Retrospective — [PHASE_TITLE]

Optional. Written manually after the implementation PR merges, when the implementation surfaced a spec gap worth remembering. `/sdd-implement-spec`'s `## Spec deviations` PR-body section is the raw material; this file is the human-curated distillation.

## Deviations from the spec

- [DEVIATION_1 — name the spec file (`requirements.md` / `plan.md` / `validation.md`), the section, and what the implementation actually had to do]
- [DEVIATION_2]

## Root cause

[ONE_OR_TWO_SHORT_PARAGRAPHS — why the spec missed this. Typical causes: missing repo context during scaffolding; an adjacent change landed after the spec was written; an assumption in the roadmap phase turned out to be wrong; a load-bearing constraint was not surfaced in `tech-stack.md`.]

## Lesson for future specs

- [LESSON_1 — actionable guidance for `/sdd-new-spec` and `/sdd-new-phase`, specific enough to apply (not generic advice). Example: "when a phase touches the broker router, the spec must remind the implementer that the broker catch-all must remain last in `src/main.py`".]
- [LESSON_2]

## Promotion candidate

[`yes` or `no` plus one sentence. Default `no` — most lessons are empirical reminders that belong in `specs/lessons.md`. `yes` only when the lesson names a load-bearing invariant that belongs in `specs/tech-stack.md`.]
