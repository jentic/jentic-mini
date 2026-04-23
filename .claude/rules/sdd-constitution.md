**Spec-Driven Development** (SDD) is a workflow where feature specs, tasks, and implementation all derive from a stable project foundation — the **constitution**. Work is grounded in the constitution rather than re-invented each time.

In this repo the constitution is one document split across three files in `specs/` — each a section, load-bearing together. None stands alone.

- `specs/mission.md` — why the project exists, who it serves, what success looks like
- `specs/tech-stack.md` — the stack that exists (not what is ideal), plus system-wide constraints and conventions
- `specs/roadmap.md` — the next shippable phases, ordered and scoped small

Each file is YAML-frontmatter-tagged with `type: constitution` and its `section:`. Do not add a `sources:` list — nothing consumes it and it rots as files move. Where a doc is load-bearing for a specific claim, cross-reference it inline in the body instead.

The constitution captures **load-bearing invariants**, not operational detail. Endpoint catalogs, schemas, threat models, and similar reference material live in `docs/` — the constitution cross-references them from `tech-stack.md`. Mission / tech-stack / roadmap is the whole set; there is no fourth section.

Supporting infrastructure:

- `.claude/templates/sdd/constitution/*.example.md` — structural templates for each section
- `.claude/prompts/create-constitution.md` — generator prompt 