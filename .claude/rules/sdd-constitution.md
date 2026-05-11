**Spec-Driven Development** (SDD) is a workflow where feature specs, tasks, and implementation all derive from a stable project foundation — the **constitution**. Work is grounded in the constitution rather than re-invented each time.

In this repo the constitution is one document split across three files in `specs/` — each a section, load-bearing together. None stands alone.

- `specs/mission.md` — why the project exists, who it serves, what success looks like
- `specs/tech-stack.md` — the stack that exists (not what is ideal), plus system-wide constraints and conventions
- `specs/roadmap.md` — the next shippable phases, ordered and scoped small

Each file is YAML-frontmatter-tagged with `type: constitution` and its `section:`. Do not add a `sources:` list — nothing consumes it and it rots as files move. Where a doc is load-bearing for a specific claim, cross-reference it inline in the body instead.

The constitution captures **load-bearing invariants**, not operational detail. Endpoint catalogs, schemas, threat models, and similar reference material live in `docs/` — the constitution cross-references them from `tech-stack.md`. Mission / tech-stack / roadmap is the whole set; there is no fourth section.

Once the constitution exists, individual roadmap phases are materialized into **feature specs** — dated directories under `specs/` (`specs/YYYY-MM-DD-<slug>/`) containing `requirements.md` (what + why), `plan.md` (how), and `validation.md` (done). Unlike constitution files, feature-spec files are plain markdown with **no YAML frontmatter** — the H1 (`# Phase N <Requirements|Plan|Validation> — <Title>`) carries identity. When a phase ships, append ` ✅` (a single space followed by the U+2705 checkmark) to its `## Phase N — Title` heading in `specs/roadmap.md` and leave the rest of the block in place (do not delete or renumber); the feature-spec directory stays as history. The leading space is load-bearing — verify steps `grep -F` for the exact ` ✅` suffix.

Supporting infrastructure:

- `.claude/templates/sdd/constitution/*.example.md` — structural templates for each constitution section
- `.claude/skills/sdd-create-constitution/SKILL.md` — `/sdd-create-constitution` skill that bootstraps the constitution from repository evidence (refuses to overwrite an existing constitution without explicit user confirmation)
- `.claude/templates/sdd/feature-spec/*.example.md` — structural templates for each feature-spec file
- `.claude/skills/sdd-new-phase/SKILL.md` — `/sdd-new-phase` skill that appends a new active phase to `specs/roadmap.md`
- `.claude/skills/sdd-new-spec/SKILL.md` — `/sdd-new-spec` skill that scaffolds a feature spec from a roadmap phase
- `.claude/skills/sdd-implement-spec/SKILL.md` — `/sdd-implement-spec` skill that implements an existing feature spec end-to-end (branch, commits per `plan.md` group, verification per `validation.md`, pre-push review pairing built-in `/review` with three deep-review subagents, PR)
