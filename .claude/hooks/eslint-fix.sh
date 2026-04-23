#!/usr/bin/env bash
# PostToolUse hook: run eslint --fix on an edited .ts/.tsx file inside ui/.
# Prettier runs via eslint-plugin-prettier, so this also reformats.
# Reads Claude Code's hook JSON from stdin and no-ops for other paths.
set -u
f=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty')
[ -n "$f" ] || exit 0
case "$f" in
  *.ts|*.tsx) ;;
  *) exit 0 ;;
esac
ui_dir=$(git rev-parse --show-toplevel 2>/dev/null)/ui
case "$f" in
  "$ui_dir"/*) ;;
  *) exit 0 ;;
esac
eslint_bin="$ui_dir/node_modules/.bin/eslint"
[ -x "$eslint_bin" ] || exit 0
cd "$ui_dir" && "$eslint_bin" --fix "$f"