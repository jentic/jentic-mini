#!/usr/bin/env python3
# PreToolUse hook: validate Conventional Commits before Claude fires `git commit`.
# Reads Claude Code's tool-input JSON from stdin. On a malformed message, emits
# a `permissionDecision: deny` JSON so the bash command never runs.
# Mirrors what .husky/commit-msg enforces for human/CI commits.
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
COMMITLINT_BIN = REPO_ROOT / "ui" / "node_modules" / ".bin" / "commitlint"


def emit_deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def extract_message(command: str) -> str | None:
    # Pattern: -m "$(cat <<'DELIM' ... DELIM)" — what Claude's CLAUDE.md prescribes.
    # Terminator anchored to start of line (MULTILINE); `<<-` form allows leading tabs/spaces.
    m = re.search(
        r"-m\s+\"?\$\(\s*cat\s+<<(-?)\s*['\"]?(\w+)['\"]?\s*\n(.*?)\n[\t ]*\2\s*$",
        command,
        re.DOTALL | re.MULTILINE,
    )
    if m:
        body = m.group(3)
        return textwrap.dedent(body) if m.group(1) == "-" else body
    # Pattern: -m "..." — bash double-quotes only escape \$ \" \\ \` (NOT \n, \t, \uNNNN).
    m = re.search(r'-m\s+"((?:[^"\\]|\\.)*)"', command)
    if m:
        return re.sub(r'\\([$"\\`])', r"\1", m.group(1))
    # Pattern: -m '...' (single quotes — no escapes in shell)
    m = re.search(r"-m\s+'([^']*)'", command)
    if m:
        return m.group(1)
    return None


def main() -> int:
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        return 0

    command = data.get("tool_input", {}).get("command", "") or ""

    # Match `git commit` allowing flags between (e.g., `git -C /path commit`, `git -c k=v commit`).
    if not re.search(r"(^|[\s&;|])git(\s+\S+)*?\s+commit(\s|$)", command):
        return 0
    # Check for `--no-edit` only in the args before -m / --message — avoid false-matching
    # the literal string inside a message body.
    args_prefix = re.split(r"\s-m\b|\s--message\b", command, maxsplit=1)[0]
    if "--no-edit" in args_prefix:
        return 0
    if not COMMITLINT_BIN.exists():
        # Fresh checkout before `npm install` — defer to husky.
        return 0

    msg = extract_message(command)
    if not msg:
        # Couldn't extract (e.g., -F file or interactive editor); husky covers it.
        return 0

    try:
        proc = subprocess.run(
            [str(COMMITLINT_BIN)],
            input=msg,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT / "ui"),
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 0

    if proc.returncode == 0:
        return 0

    output = (proc.stdout + proc.stderr).strip() or "commitlint reported errors."
    emit_deny(
        "Commit message fails Conventional Commits validation "
        "(see .claude/rules/conventional-commits.md):\n\n" + output
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
