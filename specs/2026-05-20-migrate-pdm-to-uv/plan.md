# Phase 29 Plan — Migrate Python Packaging from PDM to uv

## Group 1 — Prove `uv_build` against the `src/` layout (de-risk)

1. Edit `pyproject.toml` `[build-system]` block: replace `requires = ["pdm-backend"]` and `build-backend = "pdm.backend"` with `requires = ["uv_build>=0.8.15,<0.12.0"]` and `build-backend = "uv_build"`.
2. Append a new `[tool.uv.build-backend]` block to `pyproject.toml` immediately after `[build-system]`, with `module-name = "src"` and `module-root = ""` so uv_build vendors the existing `src/` directory unchanged into the wheel without renaming the import root.
3. Run `uv build --wheel` from the repo root and inspect the output with `unzip -l dist/jentic_mini-0.13.1-py3-none-any.whl | grep '^.*src/auth\.py'` — confirm `src/*.py` files are present in the wheel. If the wheel is empty or the override is rejected by uv_build, stop and fall back to `[build-system] requires = ["hatchling"]` + `build-backend = "hatchling.build"` plus `[tool.hatch.build.targets.wheel] packages = ["src"]` per `requirements.md` Decisions; do not proceed to Group 2 with a broken backend.

## Group 2 — Add `poethepoet` and `[tool.poe.tasks]` (additive, no removals yet)

4. Append `poethepoet>=0.37,<0.47` to `pyproject.toml` `[dependency-groups] dev` (after the existing `ruff<0.16.0,>=0.14.1` entry).
5. Add `[tool.poe.tasks]` to `pyproject.toml` (after the existing `[tool.ruff.lint.isort]` block) with three tasks: `lint` as a sequence of `ruff check ${GITHUB_ACTIONS:+--output-format=github}` (shell form) followed by `ruff format --check --diff`; `lint:fix` as a sequence of `ruff check --fix` followed by `ruff format`; `test` with `env = { PYTHONPATH = "." }` and `cmd = "pytest -v ${args:tests} --tb=short"`. The `${args:tests}` placeholder must produce identical positional-argument behaviour to PDM's `{args:tests}` (default to `tests`, allow narrow overrides).
6. Smoke each task locally before flipping anything else: `uv sync` (writes a draft lockfile but is acceptable here as a probe — discard before committing); `uv run poe lint` exits 0; `uv run poe test tests/test_health.py -v` exits 0; `uv run poe lint:fix` exits 0 with no diff. Confirm `[tool.pdm.scripts]` is still present and untouched at this point — the additive flip lets us validate poe shape against a live ruff/pytest before discarding the PDM scripts.

## Group 3 — Generate `uv.lock`, delete PDM artefacts

7. Run `uv lock` to produce `uv.lock` deterministically (this regenerates rather than upgrades, since the resolver inputs in `pyproject.toml` `[project.dependencies]` and `[dependency-groups] dev` are unchanged); commit the resulting `uv.lock`.
8. `git rm pdm.lock`; remove the working-tree `.pdm-python` interpreter marker (`git rm .pdm-python` if tracked; otherwise `rm -f .pdm-python`).
9. Edit `.gitignore`: remove the `.pdm-python` line (currently line 23). Leave `__pypackages__/` (line 22) — harmless under uv but unused.

## Group 4 — Drop `[tool.pdm.scripts]` and update the husky pre-commit hook in lockstep

10. Remove the `[tool.pdm.scripts]` block from `pyproject.toml` (currently lines 59–63). After this edit, `pyproject.toml` has zero `[tool.pdm.*]` entries.
11. Edit `.husky/pre-commit` line 1: replace `pdm run lint` with `uv run poe lint`. Leave the `cd ui && npx lint-staged` line (UI-side hook) untouched. This commit must land atomically with the `[tool.pdm.scripts]` deletion so no developer commit fails between them.

## Group 5 — Rewrite the Dockerfile

12. Edit `Dockerfile` `py-deps` stage: replace lines 15–17 (`RUN pip install --no-cache-dir pipx && pipx install pdm==2.26.9` plus the `ENV PATH="/root/.local/bin:$PATH"`) with a single multi-stage copy `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/`. Drop the `pipx` install entirely.
13. Edit `Dockerfile` line 19: change `COPY pyproject.toml pdm.lock ./` to `COPY pyproject.toml uv.lock ./`. Keep the `WORKDIR /app` (line 7) and the `RUN apt-get update … gcc libffi-dev` (lines 9–13) — these are still needed for any source-built wheels (cryptography, etc.) until proven otherwise by Group 7's CI green.
14. Edit `Dockerfile` lines 20–30: replace the entire `RUN /root/.local/bin/pdm install --prod --no-editable --no-self --frozen-lockfile && /app/.venv/bin/python -m ensurepip --upgrade && /app/.venv/bin/python -m pip install --upgrade --no-cache-dir pip setuptools wheel` block (and the comment at lines 20–27) with `RUN uv sync --frozen --no-install-project --no-dev`. The `ensurepip + pip/setuptools/wheel --upgrade` block goes away — uv's wheels avoid the bootstrap-pip CVE vector. Keep the runtime-stage `RUN python -m pip install --upgrade --no-cache-dir pip setuptools wheel` at line 40 (system pip, unrelated to PDM, with the existing comment block at lines 35–39 explaining why).
15. Confirm by inspection that lines 33+ (runtime stage) still consume the venv via `COPY --from=py-deps /app/.venv /app/.venv` (line 55) and `ENV PATH="/app/.venv/bin:$PATH"` (line 56). The `/app/.venv` shape is uv-default; no further runtime-stage edits required.

## Group 6 — Rewrite the CI workflow (`ci-backend.yml` only)

16. Edit `.github/workflows/ci-backend.yml` line 11 `paths:` filter: change `'pdm.lock'` to `'uv.lock'` so backend CI re-triggers on Dependabot's lock updates.
17. Edit `.github/workflows/ci-backend.yml` lint job (lines 28–32): replace `uses: pdm-project/setup-pdm@v4` with `uses: astral-sh/setup-uv@v6` (or current stable major); pass `python-version: '3.11'` and `enable-cache: true`. Replace `run: pdm install --dev --frozen-lockfile` (line 35) with `run: uv sync --frozen`. Replace `run: pdm run lint` (line 38) with `run: uv run poe lint`.
18. Edit `.github/workflows/ci-backend.yml` test job (lines 46–50, 53, 58): apply the identical setup-uv swap, replace the install with `uv sync --frozen`, and replace `run: pdm run test` with `run: uv run poe test`. No marker filter, no exclude list — preserve current behaviour.

## Group 7 — Flip Dependabot ecosystem

19. Edit `.github/dependabot.yml` Python entry (currently lines 13–21): change `package-ecosystem: pip` to `package-ecosystem: uv`. Leave every other field unchanged (`directory: "/"`, `schedule.interval: daily`, `schedule.time: "23:00"`, `commit-message.prefix: "chore"`, `commit-message.include: "scope"`, `open-pull-requests-limit: 3`). Leave the `npm /ui` and `github-actions /` entries entirely untouched.

## Group 8 — Update developer-facing docs

20. Edit `DEVELOPMENT.md` Prerequisites section: remove the **PDM** install line (`curl -sSL https://pdm-project.org/install-pdm.py | python3 -`) and replace with the uv install line (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
21. Edit `DEVELOPMENT.md` install section: replace `pdm venv create` and `pdm install --dev` with `uv sync` (uv creates the project-local `.venv` automatically; no separate `venv create` step).
22. Edit `DEVELOPMENT.md` "Running Tests" section: replace every `pdm run test …` invocation (currently lines 84–89) with the `uv run poe test …` equivalent, preserving the `--` argument-passthrough examples.
23. Edit `DEVELOPMENT.md` "Linting" section: replace `pdm run lint` and `pdm run lint:fix` (lines 104–110) with `uv run poe lint` and `uv run poe lint:fix`. Add a one-line note showing how to discover available poe tasks (`uv run poe`).

## Group 9 — Update agent-facing rules and SDD templates

24. Edit `.claude/rules/worktrees.md`: remove the `PDM_IGNORE_ACTIVE_VENV=1` invariant (lines 7–12 step 2 Python install paragraph and the lines 41–44 "Two env vars beyond port selection" bullet). Rewrite the host-mode launch backend block (lines 49–65) for `mkdir -p data; JENTIC_INTERNAL_PORT=8901 DB_PATH="$(pwd)/data/jentic-mini.db" uv run uvicorn src.main:app --port 8901 --reload` (no `PDM_IGNORE_ACTIVE_VENV=1` prefix). Step 2's Python install becomes `uv sync` at the worktree root.
25. Edit `.claude/rules/testing.md` line 21: replace `pdm run test …` with `uv run poe test …`.
26. Edit `.claude/rules/python-code-style.md` line 8: replace `pdm run lint:fix` with `uv run poe lint:fix`.
27. Edit `.claude/rules/update-tech-stack-on-deps.md` line 14 example list: replace `PDM` with `uv`.
28. Edit `.claude/skills/sdd-implement-spec/SKILL.md` (lines that mint `pdm run lint`/`pdm run test` into spec examples) and `.claude/skills/sdd-new-spec/SKILL.md` (same): replace each with the `uv run poe …` equivalent. Edit `.claude/templates/sdd/feature-spec/plan.example.md` line 22: replace `pdm run test tests/broker` with `uv run poe test tests/broker`.
29. Edit `.claude/settings.local.json`: replace the `Bash(pdm run *)` allowlist entry with `Bash(uv run *)` and replace the `Bash(PDM_IGNORE_ACTIVE_VENV=1 pdm update *)` entry with `Bash(uv sync *)` plus `Bash(uv lock*)`. Leave every other allowlist entry untouched.

## Group 10 — Update constitution and roadmap

30. Edit `specs/tech-stack.md` Core Stack table line 35: change `| Python packaging | PDM |` to `| Python packaging | uv |`.
31. Edit `specs/tech-stack.md` formatting/linting prose at line 92: change `PDM scripts: \`lint\`, \`lint:fix\`.` to `Poe tasks (\`[tool.poe.tasks]\`): \`lint\`, \`lint:fix\`, \`test\`.` Confirm by `grep -in pdm specs/tech-stack.md` — expect zero matches.
32. Edit `specs/roadmap.md` Phase 15 (Pyright) body bullets only: replace `[tool.pdm.dev-dependencies]` with `[dependency-groups] dev`; replace `[tool.pdm.scripts]` with `[tool.poe.tasks]`; replace `pdm run typecheck` with `uv run poe typecheck`. Do not change Phase 15's goal, priority, depends-on, or any other content.
33. Edit `specs/roadmap.md` Phase 29 heading at line 431: append ` ✅` (single space + U+2705) so the heading reads `## Phase 29 — Migrate Python Packaging from PDM to uv ✅`. Leave the rest of the Phase 29 block intact per the lifecycle rule (`specs/roadmap.md:35-40`); do not delete or renumber.

## Group 11 — Verify

34. `uv lock --check` exits 0 (lockfile is consistent with `pyproject.toml`).
35. `uv sync --frozen` exits 0 (clean install from frozen lockfile).
36. `uv build --wheel` exits 0; `unzip -l dist/jentic_mini-*.whl | grep -E 'src/(auth|db|main)\.py'` returns ≥3 lines (proves Group 1's `module-name = "src"` override held through the migration).
37. `uv run poe lint` exits 0 (ruff check + ruff format --check --diff both pass).
38. `uv run poe test` exits 0 (full backend pytest suite passes; equivalent to today's `pdm run test`).
39. `docker build -t jentic-mini:phase29 .` exits 0 (Dockerfile rewrite builds clean on the host architecture).
40. `git grep -nE "(pdm-project/setup-pdm|pdm install|pdm run|tool\.pdm)" -- ':!specs/2026-05-07-*' ':!specs/2026-05-08-*' ':!specs/2026-05-12-*'` exits 1 (no matches) — completed-spec history is excluded; everything else must be PDM-free.
41. `git grep -nE "PDM_IGNORE_ACTIVE_VENV" -- ':!specs/2026-05-07-*' ':!specs/2026-05-08-*' ':!specs/2026-05-12-*'` exits 1 (no matches outside frozen historical specs).
42. `test ! -f pdm.lock` and `test -f uv.lock` and `test ! -f .pdm-python` all exit 0.
43. `grep -F "## Phase 29 — Migrate Python Packaging from PDM to uv ✅" specs/roadmap.md` exits 0 (phase-completion lifecycle marker present, single space before ✅).
