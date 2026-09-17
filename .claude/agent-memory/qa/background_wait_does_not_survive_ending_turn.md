---
name: background-wait-does-not-survive-ending-turn
description: ending a turn to "wait" for a Bash run_in_background job does not keep you alive to receive its notification — poll in a foreground loop within one tool call instead
metadata:
  type: feedback
---

Starting a Bash command with `run_in_background: true` and then ending the turn
("I'll wait for the notification") does not reliably work the way it sounds. A
coordinator had to intervene mid-task (2026-09-02, court-mask-sweep verification) with
"you ended your turn waiting on a background job, but ending the turn is what stops
you; nothing was going to wake you." The run had in fact been executing correctly the
whole time (confirmed via `tasklist` showing rising memory on the worker process) —
the failure was procedural, not a stalled command.

**Why:** the harness's "you'll be notified when it completes" guidance describes a
background task's normal lifecycle, but a QA session that stops calling tools between
turns is not guaranteed to still be listening for that notification when it arrives —
treat "I'll wait" as equivalent to abandoning the task unless something is actively
polling within the same tool invocation.

**How to apply:** when a script takes a few minutes (e.g. `eval/run_eval.py --gold
--all --k 8`, ~4 min per its own docstring), either (a) block in a single foreground
`Bash` call with a `for`/`until` loop and `sleep`, using the tool's generous timeout
budget (up to 600000ms), and read the result at the end of that same call, or (b) if
truly backgrounding, keep issuing check-in tool calls yourself rather than ending the
turn — do not just declare "waiting" and stop. `PYTHONUNBUFFERED=1` also matters here:
a slow foreground call whose timeout expires before output flushes looks exactly like
a silent failure (buffered stdout discarded, shell reports whatever exit code the
truncation left) — suspect the timeout before suspecting the code if you see a header
print and then nothing.

See [[court-mask-sweep-item-is-already-shipped]] for the task this fired on — the
substantive finding was unaffected once re-run correctly.
