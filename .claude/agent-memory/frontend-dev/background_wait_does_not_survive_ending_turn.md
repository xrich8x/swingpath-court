---
name: background-wait-does-not-survive-ending-turn
description: never background a long-running command and then end your turn to "wait for the notification" — nothing wakes you; poll in the foreground or use partial results instead
metadata:
  type: feedback
---

**Never background a slow command and then end the turn expecting to be notified.**
A backgrounded job notifies the *coordinator*, not this agent — the coordinator then
has to send a manual restart message, which costs a full context reload. I did this
twice on the same int8-ONNX-inference wait (2026-09-02) before the coordinator named
it explicitly: "ending your turn is what stops you. Nothing wakes you." qa hit the
identical failure the same night and wrote itself the same lesson independently —
this is a real, repeatable trap for this agent role, not a one-off.

**Why:** restart overhead (re-reading the journal, memory, and task context) is a
large, avoidable cost. On this task it burned a meaningful fraction of a ~193k-token,
91-tool-call run. The fix is cheap: either poll the backgrounded job's output file
in a **foreground** loop with a bounded, generous timeout (`until [ -s file ]; do
sleep N; done`, wrapped in a single Bash call so it counts as ONE step, not several),
or — better, if the job writes incremental per-item output files (as the ONNX
parity harness does, one `.bin` per frame) — just read however many items exist
right now and use that as an honestly-labelled PARTIAL result rather than waiting
for full completion.

**How to apply:** before backgrounding anything, ask whether the answer actually
needs the full run or whether a partial, clearly-labelled sample already answers the
question (a reachability check, an outlier hunt, a rough agreement number). If a
partial answer is enough, prefer it over waiting — see the coordinator's own framing:
"a partial sample that you label honestly as partial is worth more than a complete
one that arrives after another restart." Reserve full foreground waits for cases
where the exact final number is load-bearing (a committed pre-registered gate,
not an exploratory probe).
