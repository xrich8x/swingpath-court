---
name: court-gold-provenance-is-unattributed
description: "`_exact` is a shape-lock checkbox, NOT a human-placement marker - 9 of the 20 court reference clips were placed by an agent that also judged itself"
metadata:
  type: project
---

**The 20-clip court scoring pool is not verified human ground truth, and never
was.** `eval/run_refs.py` gates it on `"_exact": true` and used to document that
flag as "the user DELIBERATELY placed these corners". False.
`tools/court_setup_server.py` writes `_exact` whenever the browser's **Shape lock
checkbox was unticked** at Save. It records nothing about who placed the corners,
and the tool cannot tell a person's mouse from an agent's HTTP POST.

**Why:** the founder reviewed the 28 rendered corner sheets on 2026-09-09 and
marked 10 wrong, certain he had not placed them. He was right. Measured by
corner-value blame (2026-09-09, `docs/evidence/calibration-provenance.md`):

- **9 of the 20** pool clips had their corner values written by the 2026-08-11/12
  agent calibration session — **seven** commits: `6a3e10f 63f304e 8c29896 209b6b5
  1b3f623 3399d58 ac94aab`. `3399d58` is the session's CLOSING commit, not its
  only one: alone it accounts for 6, and `ac94aab` contributes **zero** pool clips
  (its only value-write is `L73ep7JHiJ4`, which is not `_exact`). **Auditing by
  commit hash under-counts a batch by a third — the unit is the session.**
- `3399d58`'s message claims "all 10 were verified by eye" and, in the same
  message, retracts two of its own verdicts. It placed AND graded itself.
- **The other half of the pool is a THIRD unmentioned batch:** 10 shell clips from
  `7c8b8af` (2026-08-26, "Ten human court calibrations..."). Its "human" claim has
  the same evidentiary status — a first-person commit message, nothing in-file.
  Largest unverified block in the pool.

**How to apply:** never call these clips "human gold" or "human truth" in a
report. Say "`_exact` references, provenance unattributed". `references()` now
prints the caveat to stderr on every run — quote it rather than suppressing it.
`placed_by: "unattributed"` on new saves is an admission, not an attribution;
reading it as "human" repeats the exact error. **Nothing was re-placed** (rule 9)
— the founder owns that call and the review is open.

**Two method notes worth keeping.** (1) `git log --diff-filter=A` gives the WRONG
answer on these files: several were added by one commit of a session and re-placed
by a later one. Blame the corner VALUES by diffing non-underscore keys against
each commit's first parent. (2) `20a672e` and `1b3f623` are `_audit`-stamp-only
across the board — an audit stamp is cleanly separable from a placement.

Related: [[calibration-trap-check-corners-first]],
[[courtnet-weights-silently-substitute]], [[null-controls-and-pre-registered-populations]].
