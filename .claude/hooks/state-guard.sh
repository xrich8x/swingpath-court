#!/usr/bin/env bash
# state-guard.sh — keep docs/STATE.md honest, in every session.
# (Name kept: it is wired into .claude/settings.json by path.)
#
# docs/STATE.md is the living record: the stack, the method, and flat lists of
# what has and has not moved a number. A living document that is updated only
# when someone remembers is a stale document, and a stale scoreboard is worse
# than none — it is a confident-looking list of things that may no longer be true.
#
# So the rule is enforced by the harness rather than by anyone's memory: a commit
# that changes CODE must also stage docs/STATE.md. Runs as a PreToolUse hook on
# `git commit`, reads the hook JSON on stdin, and denies the commit with a reason
# if the scoreboard was left behind. Nothing is blocked for the USER — the denial
# goes back to Claude, which updates the file and commits again.
#
# Deliberately narrow, so it nags only when it is right to:
#   - code only. Doc-only, data-only and config-only commits pass untouched.
#   - an explicit opt-out. Put [no-state] in the commit message for a change
#     that genuinely moves no number — a typo, a rename, a revert.
#
# Test it by hand:
#   echo '{"tool_input":{"command":"git commit -m x"}}' | .claude/hooks/state-guard.sh

set -uo pipefail

allow() { exit 0; }

# No jq. It is NOT installed on the machine this repo lives on, and a hook whose
# JSON parse silently yields "" fails OPEN in a way nothing reports — the first
# version of this script did exactly that and the opt-out could never fire.
# The only thing needed from stdin is whether a distinctive literal is present,
# and a fixed-string grep over the whole payload answers that with no dependency.
input=$(cat)

# Explicit opt-out for changes that genuinely move no number.
printf '%s' "$input" | grep -qF '[no-state]' && allow

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || allow
cd "$repo_root" 2>/dev/null || allow

staged=$(git diff --cached --name-only 2>/dev/null) || allow
[ -n "$staged" ] || allow          # nothing staged: `git commit -a`, amend, or a no-op

# Already doing the right thing.
printf '%s\n' "$staged" | grep -qx 'docs/STATE.md' && allow

# Only CODE changes are gated. A doc, a dataset or a config on its own can ship
# without a scoreboard entry.
printf '%s\n' "$staged" |
  grep -qE '^(backend/|tools/|frontend/src/|mobile/|ball_physics/)' || allow

changed=$(printf '%s\n' "$staged" |
  grep -E '^(backend/|tools/|frontend/src/|mobile/|ball_physics/)' |
  head -5 | tr '\n' ' ')

cat <<JSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "docs/STATE.md is not staged, but this commit changes code ($changed). docs/STATE.md is the living record and CLAUDE.md requires it to be updated in the same commit as the work it describes. Add the entry this change earns: a shipped win with the number it moved, a measured negative with the reason it failed, a stack change, or a trap hit twice. Then 'git add docs/STATE.md' and commit again. If this change genuinely moves no number - a typo, a rename, a revert - put [no-state] in the commit message and this check will pass."
  }
}
JSON
exit 0
