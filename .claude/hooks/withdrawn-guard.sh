#!/usr/bin/env bash
# withdrawn-guard.sh — a number this project retracted must not survive somewhere else.
#
# THE FAILURE MODE THIS EXISTS FOR, measured three times:
#   a figure is corrected or withdrawn in an append-only table (What has worked /
#   has not worked, or docs/TRAPS.md) and a COPY of it lives on in the mutable "Open"
#   table,
#   which is the section the next session reads as the plan. It happened with the
#   1.47x rally over-split, then with the 1.6x that replaced it, then inside Trap T20
#   where the withdrawn figure was being used as the CORRECTIVE. Each was caught by
#   a human reading carefully. This turns that into a check.
#
# Source of truth is docs/STATE.md's "## Withdrawn figures" table: every row's
# backticked Figure is a literal string that may only appear in a block that also
# carries a withdrawal marker.
#
# BLOCK, not line, on purpose: markdown prose wraps, so "1.6×" routinely sits two
# lines above the word WITHDRAWN that governs it. A block is a run of non-blank
# lines; a table row (starts with '|') is its own block, so one row's withdrawal
# note cannot excuse the row beneath it.
#
# Historical records are skipped by design — docs/archive/HANDOFF.md, docs/archive/sessions/,
# docs/REVIEW-* and data/output/* are SUPPOSED to still contain the old number.
#
# Test by hand:
#   echo '{"tool_input":{"command":"git commit -m x"}}' | .claude/hooks/withdrawn-guard.sh

set -uo pipefail

allow() { exit 0; }

# Same no-jq reasoning as state-guard.sh: a fixed-string grep over the whole
# payload is all that is needed, and it cannot silently fail open on a parse error.
input=$(cat)
printf '%s' "$input" | grep -qF '[no-withdrawn-check]' && allow

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || allow
cd "$repo_root" 2>/dev/null || allow
[ -f docs/STATE.md ] || allow

# Live docs only. Everything else is a dated record and legitimately keeps the
# old number.
LIVE="CLAUDE.md docs/STATE.md docs/TRAPS.md ML_PRACTICES.md ML_PLAYBOOK.md README.md USER_GUIDE.md SETUP_PROMPT.md PM_REVIEW_PROMPT.md"
# docs/evidence/ is LIVE too. A result now lives half there, so a withdrawn
# figure can survive in an evidence file exactly the way it used to survive
# in the Open table - which is the failure this guard exists for.
LIVE="$LIVE $(ls docs/evidence/*.md 2>/dev/null)"

# Pull the registered figures into a shell array (one per line).
figures=$(sed -n '/^## Withdrawn figures/,/^## Open/p' docs/STATE.md \
          | grep -E '^\| `' \
          | sed -E 's/^\| `([^`]+)`.*/\1/')

[ -n "$figures" ] || allow          # nothing registered yet: nothing to enforce

report=$(
  for f in $LIVE; do
    [ -f "$f" ] || continue
    printf '%s\n' "$figures" | while IFS= read -r fig; do
      [ -n "$fig" ] || continue
      awk -v fig="$fig" -v fname="$f" '
        function flush(   i, hasfig, hasmark) {
          if (nb == 0) return
          hasfig = 0; hasmark = 0
          for (i = 1; i <= nb; i++) {
            if (index(buf[i], fig) > 0) hasfig = 1
            low = tolower(buf[i])
            if (index(low, "withdraw") > 0 || index(low, "retracted") > 0 ||
                index(low, "no longer the number") > 0 || index(low, "used to read") > 0)
              hasmark = 1
          }
          if (hasfig && !hasmark) printf "  %s:%d  `%s` with no withdrawal marker in its block\n", fname, start, fig
          nb = 0
        }
        {
          line = $0
          sub(/\r$/, "", line)
          # The registry section lists these figures by definition -
          # scanning it would make the guard permanently deny itself.
          if (line ~ /^## Withdrawn figures/) { flush(); skip = 1; next }
          else if (line ~ /^## /)             { flush(); skip = 0 }
          if (skip) next
          if (line ~ /^[ \t]*$/) { flush(); next }
          if (line ~ /^\|/) { flush(); nb = 1; buf[1] = line; start = FNR; flush(); next }
          if (nb == 0) start = FNR
          buf[++nb] = line
        }
        END { flush() }
      ' "$f"
    done
  done
)

[ -n "$report" ] || allow

# Keep the denial short enough to act on.
report=$(printf '%s\n' "$report" | head -12)
report=${report//\"/\\\"}
# Collapse to a single JSON string. The replacement is QUOTED: unquoted, bash
# eats the backslash and the message reads "...in its blockn".
report=${report//$'\n'/'\n'}

cat <<JSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "A figure listed in docs/STATE.md's 'Withdrawn figures' table still appears in a live doc without a withdrawal marker:\n\n$report\n\nThis is the exact failure this project hit three times: a number is retracted in one table and a stale copy survives in another - usually the Open table, which the next session reads as the plan. Fix it by deleting the stale figure, or by marking it withdrawn in the same block (a paragraph, or a single table row). If the file is a dated historical record it should not be in the live list at all. Genuine exception: put [no-withdrawn-check] in the commit message."
  }
}
JSON
exit 0
