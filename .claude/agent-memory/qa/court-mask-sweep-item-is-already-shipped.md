---
name: court-mask-sweep-item-is-already-shipped
description: the parked court_mask_sweep.json "12 vs 11" result is not a pending gain — surface routing shipped it 2026-08-21 (f41a489); the sweep file is a post-hoc re-banking, not a new candidate
metadata:
  type: project
---

Verified 2026-09-02 (docs/evidence/court-mask-sweep-item-is-already-shipped.md,
commit 333d38b). `data/output/court_mask_sweep.json` shows `routed_clay_chroma` and
`routed_clay_clahe` both accepting 12/20 gold clips vs `baseline`'s 11/20, and the lead
had deliberately left this un-recorded as a gate pass pending qa's check (an accept
count alone is not a gate result — the precision half matters too).

**Finding: dead, not live.** The shipped router (`calibration.court_surface` /
`court_line_mask`, from commit `f41a489`, 2026-08-21 — "Route the line mask by court
surface: clay 11/20 to 12/20, nothing lost") already IS what the sweep's routed arms
measure. Three independent confirmations now agree exactly: my own fresh
`eval/run_eval.py --gold --all --k 8` run at HEAD, the predecessor's `gate_after.log`
run, and `f41a489`'s own commit-message numbers — all 12/20 accepted, 0 wrong, median
8.1 px, range 1.7–13.9 px against the 20 gold clips' human clicks. The sweep file's
routed accept lists are byte-identical to the shipped accept list; the only clip that
ever differs is `am_rally32short`, present in shipped/routed, absent from `baseline`
(which is the PRE-routing state, not a live alternative).

`court_mask_sweep.json`'s current content was itself written a week after the ship, by
`040df9d` ("Bank the P0 sweep results and the re-run court mask sweep [no-state]",
2026-08-28) — a re-measurement banked for the record, not a new proposal.

**Why this matters:** a queue item that looks like "12 vs 11, unconfirmed" can
actually be "already shipped, unconfirmed only because nobody closed the loop." Check
the ship date of the mechanism under test against the file's own commit date before
treating a result as pending — [[qa-does-not-write-to-codebase]] has the sibling
lesson about writing this up properly once confirmed.

**What replaces it on the queue:** nothing from this file. The next court-mask idea
needs to be a genuinely new candidate; re-running what `court_line_mask()` already
does is not one. The chroma-vs-CLAHE distinction inside the sweep is real (CLAHE wins
on the 7-clip clay drop set, 6 votes to 5) but immaterial to the gold gate — both tie
there — and that drop-set number is secondary/non-gating per the pre-registered gate,
never grounds for a verdict on its own.
