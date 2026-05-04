Let's create a "constitution" in the `specs/` directory.

Create these files:
- `specs/mission.md`
- `specs/tech-stack.md`
- `specs/roadmap.md`

---

## Spec-Driven Development Context

You are operating within a Spec-Driven Development (SDD) workflow.

In SDD:
- The constitution defines the **project foundation** (mission, tech stack, roadmap)
- All future work (feature specs, tasks, implementation) will depend on this
- The goal is to be **clear, grounded, and actionable**, not exhaustive

Core principles:

1. Source of truth  
   - Reflect actual repository state and user intent  
   - Prefer evidence from code, configs, and docs over assumptions  

2. Small, iterative progress  
   - Especially in the roadmap, work must be broken into small, testable phases  
   - Avoid large, vague milestones  

3. Explicit uncertainty  
   - Clearly distinguish:
     - confirmed facts  
     - inferred conclusions  
     - unknowns requiring clarification  

4. Separation of concerns  
   - Mission = why and who  
   - Tech stack = what exists (not what is ideal)  
   - Roadmap = what comes next in small steps  

5. Agent usability  
   - Future agents will rely on this  
   - Optimize for clarity and unambiguous structure  

You are not designing a new system from scratch unless the repository is empty.  
You are documenting and structuring what exists, then extending it carefully.

Assume other agents will:
- read these files without additional context  
- generate specs from them  
- implement code based on them  

Write so they can succeed without guessing.

---

## Phase 0 — Load SDD Constitution Templates

Read reference templates:

- @.claude/templates/sdd/constitution/mission.example.md
- @.claude/templates/sdd/constitution/tech-stack.example.md
- @.claude/templates/sdd/constitution/roadmap.example.md

Extract:
- structure
- section organization
- formatting conventions
- front matter shape
- level of detail

Template rules:
- Use templates for structure only
- Do NOT copy content verbatim
- Replace all [PLACEHOLDER] values
- Adapt structure if repo suggests better organization

---

## Phase 1 — Parallel Research (MANDATORY)

Before asking questions or writing anything:

Launch parallel subagents to inspect:
- `src/` — Python code
- `ui/` — UI implementation
- `docs/` — documentation
- top-level config (requirements, pyproject.toml, package.json, Dockerfile, etc.)

Each subagent extracts:
- what the system does
- implemented capabilities
- architecture and patterns
- tech stack signals
- constraints and conventions
- gaps, risks, ambiguities
- facts relevant to:
  - mission
  - tech stack
  - roadmap

---

## Phase 2 — Synthesis

Combine findings into a single understanding:

- infer real product purpose
- infer actual tech stack (from evidence)
- determine current maturity
- identify missing pieces
- distinguish confirmed vs inferred

Rules:
- prefer repo evidence over assumptions
- track uncertainty explicitly

---

## Phase 3 — Clarifying Questions (REQUIRED)

Use AskUserQuestion tool BEFORE writing files.

Group questions into exactly:
- Mission
- Tech Stack
- Roadmap

Rules:
- ask only high-leverage unanswered questions
- minimize total questions
- do not ask what repo already answers
- surface conflicts explicitly

DO NOT write files before this step.

---

## Phase 4 — Write Constitution Files

After user answers, generate:

- `specs/mission.md`
- `specs/tech-stack.md`
- `specs/roadmap.md`

---

## Front Matter Requirements

Each file MUST include YAML front matter.

Required fields:
- type: constitution
- section: mission | tech-stack | roadmap
- generated_by: spec-driven-agent
- generated_at: ISO timestamp
- confidence: low | medium | high

Rules:
- do NOT add a `sources:` list — nothing consumes it and it rots as files move
- cross-reference load-bearing docs inline in the body instead (e.g. "see `docs/auth.md`")
- keep metadata lightweight
- do not duplicate content from body

---

## File Requirements

### mission.md
- purpose of the project
- target users / stakeholders
- problem being solved
- success criteria
- align with repo reality
- include assumptions if uncertain

---

### tech-stack.md
- describe actual current stack (not ideal)
- include:
  - language, frameworks, libraries
  - UI approach
  - data/storage
  - testing
  - tooling
  - runtime/deployment clues

Rules:
- separate confirmed vs inferred
- do NOT present recommendations as facts
- only list “not used” when supported by evidence

---

### roadmap.md
- define small, incremental phases
- each phase must be:
  - testable
  - reviewable
  - independently valuable

Rules:
- prefer vertical slices
- avoid “build backend/frontend” phases
- start from current repo state
- include phase dependencies
- keep phases small (hours to days, not weeks)

---

## Quality Bar

- do NOT invent facts
- do NOT leave [PLACEHOLDER] unresolved
- prefer evidence over assumptions
- produce clear, structured markdown
- optimize for future agents

---

## Conflict Handling

If:
- repo evidence conflicts with user input
- or ambiguity remains

STOP and surface the conflict before proceeding.

---

## Goal

Produce a clear, evidence-based constitution that future spec-driven development can reliably build upon.