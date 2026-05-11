---
name: sdd-create-constitution
description: Bootstrap the SDD constitution (specs/mission.md, specs/tech-stack.md, specs/roadmap.md) from current repository evidence. Refuses by default if any of the three files already exists — overwriting requires explicit confirmation via AskUserQuestion. Loads the constitution templates, runs parallel Explore subagents over src/, ui/, docs/, and top-level config to ground claims in evidence, synthesizes findings, then issues a single grouped AskUserQuestion call (Mission / Tech Stack / Roadmap) before writing the three files. Edits files in place and stops — committing, branching, and opening a PR are user actions.
argument-hint: "(no arguments)"
---

# /sdd-create-constitution — bootstrap the SDD constitution

You are operating within a Spec-Driven Development (SDD) workflow. See `.claude/rules/sdd-constitution.md`.

The **constitution** is the project foundation that every later SDD action (feature specs, tasks, implementation) derives from. It lives in `specs/` as three files: `mission.md` (why and who), `tech-stack.md` (what exists), `roadmap.md` (what comes next, in small phases). This skill bootstraps those three files from current repository evidence — code, configs, dependencies, docs — rather than aspiration. Once the constitution exists, future phases are appended via `/sdd-new-phase` and materialized into feature specs via `/sdd-new-spec`. This skill is the cold-start; it is not for incremental updates.

## Hard constraints

- **Refuse to overwrite without explicit user confirmation.** If `specs/mission.md`, `specs/tech-stack.md`, or `specs/roadmap.md` already exists, the skill stops at Phase 0 and asks the user via `AskUserQuestion` whether to overwrite. Default-deny: anything other than an explicit "overwrite all three files" selection aborts the run. Do not auto-backup, rename, or move existing files — the user owns them.
- **Do not write to disk before the Phase 4 AskUserQuestion completes.** The grouped clarifying questions lock in decisions that shape file content; writing earlier wastes the call.
- **Ground every claim in repository evidence.** Prefer facts from `src/`, `ui/`, `docs/`, `pyproject.toml`, `package.json`, `Dockerfile`, and similar over assumptions. Use `Explore` subagents for parallel research; do not invent capabilities, libraries, or constraints the repo does not support.
- **Distinguish confirmed facts from inferred conclusions and unknowns.** Mark uncertainty inline; do not present inferences as facts.
- **No git actions, no commits, no branching.** This skill writes files and stops. Branching, committing, and PR creation are user actions per `.claude/rules/git-workflow.md`.
- **Templates are structural scaffolds, not content.** Replace every `[PLACEHOLDER]`; do not copy template prose verbatim.
- **Front matter shape is fixed.** Each file starts with YAML frontmatter: `type: constitution`, `section: mission|tech-stack|roadmap`, `generated_by: spec-driven-agent`, `generated_at: <ISO 8601 UTC timestamp>`, `confidence: low|medium|high`. Do **not** add a `sources:` list — nothing consumes it and it rots; cross-reference load-bearing docs inline in the body instead.
- **If the repo is empty (no code, no configs)**, stop and tell the user — there is nothing to ground a constitution against. The skill documents and structures what exists; it does not design from scratch.

## Phase 0 — Existence guard (MANDATORY, before any work)

Check for the three constitution files in parallel:

- `specs/mission.md`
- `specs/tech-stack.md`
- `specs/roadmap.md`

**If none exist** — proceed silently to Phase 1.

**If any exist** — stop and surface the situation. List which of the three files exist with their last-modified date and byte size so the user can judge what would be overwritten. Then issue a single `AskUserQuestion` call:

  - Prompt: "A constitution already exists in `specs/`. The files listed above will be overwritten if you continue. Proceed?"
  - Options:
    - `Cancel — keep existing constitution` (recommended; first option)
    - `Overwrite all three files`
  - The freeform write-in is provided automatically. Treat **every** freeform write-in as cancel — only the explicit `Overwrite all three files` option-button selection proceeds.

Only proceed past this gate if the user explicitly selects the `Overwrite all three files` option button. Anything else — including silence, cancel, or any freeform write-in regardless of its content — aborts the run with a one-line summary ("Aborted; existing constitution preserved.").

If only one or two of the three files exist (a partial constitution), the same rule applies: any existing file means the guard fires. The skill regenerates all three together; it does not patch individual sections.

## Phase 1 — Load constitution templates

Load the three structural templates in parallel:

- @.claude/templates/sdd/constitution/mission.example.md
- @.claude/templates/sdd/constitution/tech-stack.example.md
- @.claude/templates/sdd/constitution/roadmap.example.md

Extract structure, section organization, formatting conventions, frontmatter shape, and level of detail. Use the templates as scaffolds for the files you generate — do not copy their prose verbatim.

## Phase 2 — Parallel research (MANDATORY)

Launch four `Explore` subagents in parallel — a single message with multiple `Agent` tool calls, `subagent_type: Explore`, one per research area. Do not proceed to Phase 3 until all four return.

- **Thoroughness:** `very thorough` on every subagent. The constitution is load-bearing; shallow grounding produces a shallow constitution that future agents will misuse.
- **Briefs are self-contained.** Each subagent does not see this conversation. Include the goal (constitution bootstrapping) and the specific area to inspect.

**Subagent A — Backend research** (`src/`):
- What does the system do (routes, request flow, core modules)?
- Implemented capabilities (search, broker, workflows, credentials, etc.)
- Architecture invariants and constraints (e.g. router registration order, middleware chain, DB access patterns)
- Tech-stack signals (dependencies, runtime/server choice)
- Return: confirmed capabilities, architectural invariants, uncertainty markers.

**Subagent B — UI research** (`ui/`):
- What admin/user interface ships (pages, primary flows)
- UI tech stack (framework, styling system, build tool, generated API client)
- Design conventions (theming approach, component library, where generated code lives)
- Return: capabilities visible in the UI, UI stack facts, conventions worth preserving.

**Subagent C — Documentation research** (`docs/`, `README.md`, `AGENTS.md`, `CLAUDE.md`):
- Stated mission and product purpose
- Documented architecture and constraints
- User personas / target audiences mentioned
- Threat models, design decisions, load-bearing invariants
- Return: stated facts about why the project exists, who it serves, what is load-bearing.

**Subagent D — Top-level config research** (`pyproject.toml`, `package.json`, `Dockerfile`, `compose.yml`, CI workflows under `.github/`, `.editorconfig`, `.tool-versions`):
- Languages, runtimes, build tools, deployment shape
- Test frameworks and CI gates
- Linting / formatting / type-checking choices
- Return: tech-stack evidence with file references.

**Rules:**
- Every brief must instruct the subagent to lead its summary with a `## Blockers` section (write `_none_` when there are none). Examples of blockers: the repo is empty (nothing to ground a constitution); critical files referenced from `CLAUDE.md` or `AGENTS.md` are missing; the repo contains multiple disjoint projects with unclear scope.
- Subagents are read-only (`Explore` type; cannot edit, write, or commit).
- If any subagent returns a non-empty `## Blockers` section, stop and report to the user before Phase 3.

## Phase 3 — Synthesis

Combine the four research summaries into a single understanding:

- Real product purpose (mission)
- Actual tech stack from evidence (not aspirational)
- Current maturity (prototype / early-stage / production)
- Gaps and missing pieces relevant to the roadmap
- Conflicts between sources (e.g. `README.md` claims X but `src/` shows Y) — surface these explicitly; do not paper over them

Track three categories explicitly: **confirmed facts**, **inferred conclusions**, **unknowns requiring clarification**. Carry these into Phase 4 — they determine which questions are worth asking and which are answered by evidence already.

If synthesis surfaced material conflicts, raise them to the user as a freeform note before issuing the Phase 4 AskUserQuestion call. Do not silently pick a side.

## Phase 4 — AskUserQuestion (MANDATORY, before any disk write)

Issue a single `AskUserQuestion` call containing exactly three questions, one per output file. Each question offers 3–4 concrete options derived from the synthesis. Ask only **high-leverage unanswered questions** — do not ask what the repo already answers.

**Question 1 — Mission** (shapes `specs/mission.md`):
  - Prompt: a one-sentence question resolving the largest mission unknown surfaced in synthesis (typically: who the primary stakeholder is, or what the core problem framing is).
  - Options: 3–4 framings derived from synthesis; if synthesis already resolves this, offer "the synthesis framing already fits — proceed as drafted" as a recommended option.

**Question 2 — Tech Stack** (shapes `specs/tech-stack.md`):
  - Prompt: a one-sentence question resolving the largest tech-stack uncertainty surfaced in synthesis (typically: current maturity level, or whether a partially-evident technology is actually load-bearing).
  - Options: 3–4 evidence-grounded options; if synthesis already resolves this, offer the proceed-as-drafted option.

**Question 3 — Roadmap** (shapes `specs/roadmap.md`):
  - Prompt: a one-sentence question resolving the next-priority direction or scope (typically: which gap from synthesis to address first, or what the immediate next phase looks like).
  - Options: 3–4 plausible next-phase directions derived from gaps; if synthesis already implies a clear sequence, offer the proceed-as-drafted option.

Only after the user answers all three do you proceed to Phase 5.

## Phase 5 — Write the three files

Write `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md` using the templates from Phase 1 as structural scaffolds and the synthesis + user answers as content. Each file MUST start with the YAML frontmatter from Hard constraints — fill `generated_at` with the current ISO 8601 UTC timestamp and `confidence` per how well grounded the section is in evidence.

### mission.md

- Purpose of the project — why it exists, in real-world terms
- Target users / stakeholders
- Problem being solved
- Success criteria — measurable outcomes, observable behavior, concrete capabilities
- Align with repo reality; surface assumptions explicitly when uncertain

### tech-stack.md

- Describe the **actual current** stack (not the ideal stack)
- Cover: language, frameworks, libraries, UI approach, data/storage, testing, tooling, runtime/deployment
- Separate confirmed vs inferred — do not present recommendations as facts
- Include "What We Are Not Using" entries only when supported by evidence
- Cross-reference load-bearing docs from `docs/` inline (e.g. "see `docs/architecture.md`") rather than enumerating them in frontmatter

### roadmap.md

- Define small, incremental phases — each one shippable, independently reviewable, testable
- Prefer vertical slices (a phase touches whatever layers it needs to deliver an end-to-end capability) over technical-layer splits ("build the backend", "build the frontend")
- Include `Depends on:` between phases when ordering matters
- Keep phases small (hours to days, not weeks); split if a phase feels too large
- Use `Priority:` values per the template — `High`, `Medium–High` (with the en-dash U+2013, not a hyphen), `Medium`. Apply `(blocker)` only when the phase fixes a current trust/security gap that makes the system unsafe for its intended use **today**; forward-looking production work uses normal priority and states the rationale in the phase body.
- Include a **Lifecycle** paragraph near the top of the file describing the completion-marker convention: when a phase ships, append ` ✅` (a single space followed by the U+2705 checkmark) to its `## Phase N — Title` heading and leave the rest of the block in place (do not delete or renumber). The leading space is load-bearing — completion-verify steps `grep -F` for the exact ` ✅` suffix. Phase numbers are stable identifiers; completed phases stay in the file as history. New work takes the next number after the largest existing phase. Pair this with a one-line intro at the top: "Phases marked `✅` have shipped; everything else is planned."

## Phase 6 — Report back

Return to the user in a few lines:

- Files created (full paths) — three of them
- Confidence levels recorded in each file's frontmatter, with a one-line rationale per level
- Conflicts surfaced during synthesis (if any) and how they were resolved
- Next steps (user-driven — this skill does not do them):
  1. Review the diff (`git diff specs/`).
  2. Branch + commit + PR per `.claude/rules/git-workflow.md` and `.claude/rules/conventional-commits.md` (suggested header: `docs(specs): bootstrap SDD constitution`).
  3. Once merged, use `/sdd-new-phase` to add active phases beyond what was bootstrapped, and `/sdd-new-spec <N>` to materialize a phase into a feature spec.

If the run aborted at the Phase 0 guard, the report is a single line — no Phase 6 sections, just confirmation that the existing constitution was preserved.
