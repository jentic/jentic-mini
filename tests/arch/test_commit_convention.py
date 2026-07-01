"""Lock the conventional-commit contract enforced by the commit-msg hook.

The ``commit-msg`` lefthook command runs ``uv run cz check``, which validates
messages against ``[tool.commitizen.customize].schema_pattern`` in
``pyproject.toml``. This test asserts that pattern's behaviour directly so the
repo-wide commit convention (mandatory ``type(scope): subject`` per
``.cursor/rules/git-conventions.mdc``) can't silently regress if the config is
edited. It reads the live pattern from ``pyproject.toml`` — no Node, no cz
binary, no subprocess.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
CONVENTIONS = REPO_ROOT / ".cursor" / "rules" / "git-conventions.mdc"

VALID_MESSAGES = (
    "feat(ui): add SPA static serving to the admin surface",
    "fix(security): reject unknown fields in permission rules",
    "ci(ci.yml): cache uv downloads between runs",
    "refactor(broker): extract credential minting helper",
    "chore(deps): bump fastapi to 0.118",
    "docs(readme): document the local UI workflow",
    "feat(admin)!: drop legacy users endpoint",
    "build(docker): add ui-builder stage to the base image",
    "revert(web): undo the SPA prefix change",
)

INVALID_MESSAGES = (
    "fix: missing scope here",  # no scope — violates mandatory-scope rule
    "updated some stuff",  # not conventional at all
    "wibble(ui): unknown type",  # type not in the allowed set
    "feat (ui): space before scope",  # malformed header
    "Feat(ui): capitalised type",  # type must be lower-case
    "bump(deps): not an allowed type",  # 'bump' dropped to match git-conventions.mdc
)


def _schema_pattern() -> str:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    pattern = data["tool"]["commitizen"]["customize"]["schema_pattern"]
    assert isinstance(pattern, str) and pattern, "schema_pattern must be a non-empty string"
    return pattern


def _schema_types() -> set[str]:
    """The type alternation `(feat|fix|...)` from the live schema_pattern."""
    match = re.search(r"\(([a-z|]+)\)", _schema_pattern())
    assert match, "schema_pattern must contain a type alternation group like (feat|fix|...)"
    return set(match.group(1).split("|"))


def _conventions_table_types() -> set[str]:
    """The `| `type` | ...` rows from the in-repo git-conventions.mdc table."""
    text = CONVENTIONS.read_text(encoding="utf-8")
    return set(re.findall(r"^\|\s*`([a-z]+)`\s*\|", text, flags=re.MULTILINE))


@pytest.mark.arch
@pytest.mark.parametrize("message", VALID_MESSAGES)
def test_valid_commit_messages_pass(message: str) -> None:
    assert re.match(_schema_pattern(), message), (
        f"Expected a valid conventional commit to pass schema_pattern: {message!r}"
    )


@pytest.mark.arch
@pytest.mark.parametrize("message", INVALID_MESSAGES)
def test_invalid_commit_messages_fail(message: str) -> None:
    assert not re.match(_schema_pattern(), message), (
        f"Expected a non-conforming commit to be rejected by schema_pattern: {message!r}"
    )


@pytest.mark.arch
def test_conventions_doc_table_matches_schema() -> None:
    """The git-conventions.mdc type table is the human source of truth for the
    enforced regex; they must not drift. Both are loaded live, so adding a type
    in one place without the other fails here."""
    schema_types = _schema_types()
    doc_types = _conventions_table_types()
    assert doc_types == schema_types, (
        "Commit types in .cursor/rules/git-conventions.mdc drifted from the "
        f"pyproject schema_pattern. Doc-only: {sorted(doc_types - schema_types)}; "
        f"schema-only: {sorted(schema_types - doc_types)}."
    )
