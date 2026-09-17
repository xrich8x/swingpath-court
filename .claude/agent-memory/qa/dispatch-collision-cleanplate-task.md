---
name: dispatch-collision-cleanplate-task
description: 2026-09-06 the lead dispatched qa AND backend-dev to the same clean-plate-MTI deliverable path concurrently; also SendMessage was not actually in qa's toolset despite the brief
metadata:
  type: feedback
---

On 2026-09-06 my task brief told me to `SendMessage` `backend-dev` about a coupled clean-
plate/MTI measurement question. **No `SendMessage` tool was present in my actual toolset**
(Read/Write/Edit/Bash/Grep/Glob only) — the brief's premise was wrong. Worked around it by
reading `backend-dev`'s journal and evidence file directly as a one-way, no-coordination
channel — reads work, but I could not signal back or get a reply before finishing.

Separately, backend-dev's own journal showed it running, **at the same time, the literal
same task**: same deliverable path (`docs/evidence/cleanplate-mti-measured.md`), same
script under test, its own independently pre-registered bar. This is a **duplicate
dispatch**, not a division of labour — two agents were both writing to one file path. I did
not overwrite backend-dev's content (wrote my own file first since it wasn't there yet;
backend-dev's own `near-line-detection-precision.md` file, a DIFFERENT path, appeared later
mid-run with its shared protocol).

**Why:** looks like the founder/lead posed a single question ("does temporal integration
help the near-baseline+net-line solve") and independently briefed both qa and backend-dev
to measure it, without registering that both briefs pointed at the same output file.

**How to apply:** if a future brief tells me to coordinate with another named teammate on a
"coupled question," check that teammate's journal EARLY (before doing expensive
measurement work) — not just for its protocol, but to check whether it has literally been
given my same deliverable path. If so, flag the collision in the report immediately and
keep working (do not stop), since the lead — not either agent — resolves collisions. Do not
assume a brief's claimed tool (`SendMessage`) actually exists; check the real tool list
first and route around it via journals/evidence files if it's missing, and say so plainly
in the report rather than quietly failing to "message" anyone.

See also [[cleanplate-mti-near-baseline-measured]].
