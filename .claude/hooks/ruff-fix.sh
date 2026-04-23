#!/usr/bin/env bash
# PostToolUse hook: run ruff check --fix and ruff format on an edited .py file.
# Reads Claude Code's hook JSON from stdin and no-ops for non-Python paths.
set -u
f=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty')
[ -n "$f" ] && [ "${f##*.}" = "py" ] || exit 0
ruff check --fix "$f" && ruff format "$f"