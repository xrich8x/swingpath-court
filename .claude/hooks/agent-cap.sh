#!/usr/bin/env bash
# agent-cap.sh — thin wrapper. All logic lives in agent_cap.py; see its docstring.
#
# The wrapper exists to pick an interpreter and to FAIL OPEN if it cannot find one, the
# same discipline as the sibling guards: a broken guard must never wedge the session.
# Note `python`/`python3` on this machine are Microsoft Store shims that print an ad and
# exit non-zero, so the probe runs each candidate before trusting it.

set -uo pipefail
allow() { exit 0; }

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || allow
[ -f "$repo_root/.claude/hooks/agent_cap.py" ] || allow

PY=""
for c in py python3 python; do
  command -v "$c" >/dev/null 2>&1 || continue
  "$c" -c "pass" >/dev/null 2>&1 || continue
  PY="$c"; break
done
[ -n "$PY" ] || allow

exec "$PY" "$repo_root/.claude/hooks/agent_cap.py"
