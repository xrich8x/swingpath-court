#!/usr/bin/env bash
# claude-md-cap.sh — refuse a commit that pushes CLAUDE.md past its context budget.
#
# WHY THIS IS A HOOK AND NOT A PARAGRAPH: CLAUDE.md is auto-loaded every session and
# every line costs context on every turn. It reached 470 lines by accretion — a
# session log, a per-file calibration table, four subsystem walkthroughs — none of
# which any single turn needed. Nothing stopped that except someone noticing, and
# nobody did for months. A cap that is only remembered is a cap that gets forgotten.
#
# The number is a budget, not a style rule: at ~150 non-blank lines the file is
# roughly 8 KB, which is what a fresh session should pay for orientation.
#
# Test by hand:
#   echo '{"tool_input":{"command":"git commit -m x"}}' | .claude/hooks/claude-md-cap.sh

set -uo pipefail

allow() { exit 0; }

# Same no-jq reasoning as the sibling guards: a fixed-string grep over the whole
# payload is all that is needed, and it cannot silently fail open on a parse error.
input=$(cat)
printf '%s' "$input" | grep -qF '[no-cap]' && allow

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || allow
cd "$repo_root" 2>/dev/null || allow
[ -f CLAUDE.md ] || allow

CAP=150
LINES=$(grep -cve '^[[:space:]]*$' CLAUDE.md)

[ "$LINES" -gt "$CAP" ] || allow

over=$((LINES - CAP))

cat <<JSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "CLAUDE.md is $LINES non-blank lines, $over over the $CAP cap.\n\nThis file is auto-loaded every session, so every line costs context on every turn. It is orientation, not storage. Move the new material to whichever of these owns it:\n\n  Findings, numbers, verdicts -> docs/STATE.md (one line + an evidence path)\n  Mechanism, war story, caveats -> docs/evidence/<slug>.md\n  Session history -> docs/session_log.md\n  A process mistake hit twice -> docs/TRAPS.md (append a new ID, never renumber)\n  Subsystem detail -> docs/modules.md\n  Calibration residuals -> docs/calibration.md\n\nIf the new lines genuinely belong in CLAUDE.md, cut something else to make room - the cap is the point. Genuine exception: put [no-cap] in the commit message."
  }
}
JSON
exit 0
