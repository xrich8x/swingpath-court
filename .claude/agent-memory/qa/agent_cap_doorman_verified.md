---
name: agent-cap-doorman-verified
description: Independent verification of the concurrency-cap hook (agent_cap.py) and journal system, 2026-08-28 — what's solid, what's a real gap
metadata:
  type: project
---

Verified `.claude/hooks/agent_cap.py` + `agent-cap.sh` (the "doorman") and the journal
system end to end on 2026-08-28, by feeding synthetic hook payloads directly to the
script — never by re-deriving the logic by reading it. All 10 items in the brief were
checked; full numbers are in that day's report to the lead, not duplicated here.

**Solid (measured, not just read):** cap denies at exactly live>=3 (allow at 0/1/2, deny
at 3/4); every malformed-input shape (bad JSON, empty stdin, plain text, no git repo,
no python on PATH) fails open silently; parking stores `tool_input` verbatim (model +
full prompt) at `.claude/.agent-queue/<sha1-16>.json`; hand-back at Stop emits
`continue:true` + `additionalContext` with the original args and is bounded — offered on
handbacks 1/2/3, dropped with a systemMessage on the 4th; a normally-redispatched
identical `tool_input` self-clears its queued twin (task_key is a sorted-JSON sha1, so
key order doesn't matter); TTL sweep actually removes a lock backdated past 1800s and the
live count reflects the removal in the same call. Root resolution (`Path(__file__).
resolve().parents[2]` in Python, `git rev-parse --show-toplevel` in the wrapper) is
robust to cwd — confirmed correct even when invoked from an unrelated untracked
subfolder inside the repo.

**Real gaps found, not fixed (not my job) — worth a human look:**
1. **TOCTOU race, demonstrated not just argued.** The PreToolUse check has ZERO side
   effect on the live count — locks are only written later at `SubagentStart`. Fired two
   independent PreToolUse checks back-to-back against the same 1-free-slot state with no
   lock created in between: both returned allow. If the lead ever dispatches multiple
   Agent calls in one message (CLAUDE.md tells it to do exactly this) while only 1 slot
   is free, nothing in this code prevents all of them passing. Whether the harness
   serializes tool-call hooks enough to close this in practice is unverified — did not
   test with real concurrent agents (would have corrupted the very measurement).
2. **`safe_name()` collision, demonstrated live.** Two different `agent_id` values
   differing only by punctuation (`team:agent.7` vs `team/agent 7`) sanitize to the
   identical lock filename `team_agent_7`; firing both as separate `SubagentStart`
   events produced ONE lock file, not two — an undercount. Whether real Claude Code
   `agent_id`s can ever contain such characters is unknown from inside this repo (no
   schema doc found) — flag, don't assume exploitable.
3. **Silent truncation over `MAX_PROMPT_ECHO` (8000 chars).** The queue file itself
   stores the full prompt verbatim regardless of length (confirmed at 9000 chars). But
   the Stop-event hand-back's `additionalContext` truncates to 8000 chars with **no
   truncation notice in the message** — a human re-reading the hand-back would not know
   it was cut. Only matters for prompts over 8000 chars; typical dispatch prompts
   round-trip fully.
4. Hook `timeout: 10` in settings.json — fail-open vs fail-closed on an actual timeout
   is a Claude-Code-harness behavior, not this repo's code; not tested (would require
   deliberately hanging a hook mid-session).

Journals: all 6 exist (5 agents + lead) and are git-tracked; each agent role file's
"Your journal" section names its own correct path; `.gitignore` correctly excludes
`.claude/.agent-locks/` and `.claude/.agent-queue/`. `lead.md`'s RESTART CHECKLIST
claims (30-min TTL, queue survives a session, locks reconcilable against `ListAgents`)
all check out against the code — TTL is genuinely 1800s (`TENNIS_AGENT_TTL` unset
anywhere, so the code default holds), no env override for CAP either (genuinely 3).

**Environment note, not a code finding:** this session's declared "working directory"
(`...\Swing Vision\master references`) is NOT the project root — it's an untracked
subfolder inside the real repo with unrelated generic content and its own empty
auto-created `.claude/agent-memory` stub (which is why my first memory-read attempt at
that path 404'd). The real, populated `.claude/` (hooks, journals, agent-memory with
actual history) is one level up at `...\Swing Vision\.claude\`. Used that as root
throughout. Worth a human checking whether this is a harness cwd bug or a deliberately
placed decoy folder — did not touch it beyond confirming it's inert.
