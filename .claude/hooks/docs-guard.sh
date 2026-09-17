#!/usr/bin/env bash
# docs-guard.sh — keep the USER-FACING docs honest when the user-facing surface moves.
#
# docs/STATE.md is already enforced by state-guard.sh (any code change must
# record what it moved). This is the second half of the same idea, and it exists
# because of a measured failure: for weeks every install instruction in the repo
# told the reader to run `python`, which on this machine prints "Python was not
# found" and installs nothing. Nobody noticed, because everyone working on the
# repo used the venv interpreter directly — the docs were wrong in a way only a
# NEWCOMER would hit.
#
# So this gate is deliberately NARROW. It fires on exactly one thing: a change to
# the CLI surface (backend/run.py's argument parser) without touching a
# user-facing doc. That is the case where a stale doc actively misleads — a flag
# that no longer exists, or a new one nobody is told about.
#
# It does NOT demand a doc edit for every code change. A gate that cries wolf gets
# bypassed, and a bypassed gate is worse than none.
#
# Runs as a PreToolUse hook on `git commit`, reads the hook JSON on stdin, and
# denies with a reason. Nothing is blocked for the USER — the denial goes back to
# Claude, which updates the doc and commits again.
#
# Test it by hand:
#   echo '{"tool_input":{"command":"git commit -m x"}}' | .claude/hooks/docs-guard.sh

set -uo pipefail

allow() { exit 0; }

input=$(cat)

# Same explicit opt-out as the scoreboard guard, for a change that genuinely
# alters no user-facing behaviour (a rename, a comment, a revert).
printf '%s' "$input" | grep -qF '[no-docs]' && allow

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || allow
cd "$repo_root" 2>/dev/null || allow

staged=$(git diff --cached --name-only 2>/dev/null) || allow
[ -n "$staged" ] || allow

# Only fire when the CLI entry point itself changed.
printf '%s\n' "$staged" | grep -qx 'backend/run.py' || allow

# Did the change actually touch the ARGUMENT PARSER? A refactor inside a command
# body does not change what a user types, so it should not demand a doc edit.
if ! git diff --cached -U0 -- backend/run.py |
     grep -E '^[+-]' | grep -qE 'add_argument|add_parser|set_defaults'; then
  allow
fi

# A user-facing doc must move with it.
printf '%s\n' "$staged" | grep -qE '^(README\.md|USER_GUIDE\.md|SETUP_PROMPT\.md|CLAUDE\.md)$' && allow

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "backend/run.py's ARGUMENT PARSER changed (add_argument / add_parser / set_defaults) but no user-facing doc is staged. The commands people type just changed, so at least one of README.md, USER_GUIDE.md, SETUP_PROMPT.md or CLAUDE.md must change with it - a flag that no longer exists, or a new one nobody is told about, is worse than no doc. USER_GUIDE.md section 5 lists the analyze flags; README.md has the workflow; CLAUDE.md has the Commands block. Update whichever is now wrong, 'git add' it, and commit again. If this genuinely changes nothing a user types - a rename, a comment, a revert - put [no-docs] in the commit message."
  }
}
JSON
exit 0
