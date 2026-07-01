"""Guard against reintroducing the removed "system" user/actor notion.

Every write path must thread a real ``Identity`` (user, agent, or service
account) for audit provenance and ``created_by`` columns. There is no longer a
``system`` fallback actor: the ``ActorType`` enum has no ``SYSTEM`` member and no
source file may use the bare literal ``"system"`` as an actor/created_by value.

The ``Origin.SYSTEM`` enum member is excluded — it represents a request-origin
surface (not an actor type) and is orthogonal to actor identity.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.arch.conftest import SRC_ROOT, python_files_in

_EXCLUDED_FILES = frozenset(
    {
        SRC_ROOT / "shared" / "models" / "actors.py",
    }
)


def _violations(path: Path) -> list[str]:
    """Return offending references to a system actor in a source file."""
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []

    found: list[str] = []
    for node in ast.walk(tree):
        # ActorType.SYSTEM attribute access (the enum member no longer exists).
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "SYSTEM"
            and isinstance(node.value, ast.Name)
            and node.value.id == "ActorType"
        ):
            found.append(f"ActorType.SYSTEM (line {node.lineno})")
        # The bare literal "system" used as an actor/created_by value. An exact
        # match avoids false positives on substrings like "system:metrics" or
        # "filesystem".
        elif isinstance(node, ast.Constant) and node.value == "system":
            found.append(f'literal "system" (line {node.lineno})')
    return found


@pytest.mark.arch
def test_no_system_actor_in_src() -> None:
    """No source file may reference a "system" actor or created_by value."""
    offenders: list[tuple[str, list[str]]] = []
    for path in python_files_in(SRC_ROOT):
        if path in _EXCLUDED_FILES:
            continue
        hits = _violations(path)
        if hits:
            offenders.append((str(path.relative_to(SRC_ROOT)), hits))

    assert not offenders, (
        'The "system" actor/created_by notion has been removed. Thread a real '
        "Identity (actor_type=identity.actor_type, actor_id/created_by="
        "identity.sub) instead of falling back to a system actor:\n"
        + "\n".join(f"  {f}: {hits}" for f, hits in offenders)
    )
