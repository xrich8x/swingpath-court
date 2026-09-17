---
name: court-proposal-recall-search-binds
description: Measured 2026-09-09 — court proposal recall 8/20 gold refs, 1/5 shell recordings; SEARCH binds, criteria do not (19/20); mount-height mechanism failed its pre-registered bar
metadata:
  type: project
---

**Court candidate proposal recall, measured 2026-09-09 by `eval/candidate_audit.py --k 8`
over `eval/run_refs.references()` (20 human `_exact:true` calibrations).**
Evidence: `docs/evidence/candidate-proposal-recall.md`.

**Why:** the external research doc's #3 insight — a proposal stage that only offers
geometrically "obvious" candidates caps everything downstream. It gated backend-dev's
CNN-global/classical-local reorder.

**How to apply:** these are the reference numbers for "which court stage binds". Quote
the population every time; there are two different 20-clip court pools in this repo.

## The numbers

- **Proposal recall 8/20 = 40%.** Pre-registered bar (written before the run): search
  binds <=0.60, voting binds >=0.80. **SEARCH BINDS.** Robust across tolerance 20-35 px
  (8/20 at 20-22 px, 10/20 at 30-35 px).
- **Shell 2/10 clips = 1/5 recordings** — exactly ON my pre-registered <=1/5 shell line,
  so **borderline** search-binds. 3 of 10 shell clips produce **no lock at all**.
  Only `flexi_franz` ever reaches truth. On the 4 shell recordings whose truth is
  trustworthy (`mpc_tuesday`'s two labels disagree by 25.4 px, above the wrong-court
  line) it is **1/4 recordings, 2/8 clips**.
- Hardcourt 4/8 clips (3/7 recordings), Clay 2/2.
- **Mount height: FAILED its pre-registered mechanism bar.** <2.0 m 4/12 = 33.3% vs
  >=2.0 m 4/8 = 50.0%; gap 16.7 pp against a 40 pp bar. Also confounded — 8 of the 12
  sub-2 m clips are shell. Surface separates the data; height does not.
- Best-candidate errors are trimodal, and "refused" hides all three: near miss (2 clips,
  23.1 and 27.6 px), wrong court (15 clips, 35-111 px), nothing produced (3 clips).

## The trap I nearly fell into — and the correct accept-side number

`candidate_audit.py` prints `truth_would_pass = 9/20`. **Do not quote it.** It scores the
EXACT human clicks and fails a clip if any 1 of 8 frames fails any term — the identical
artifact that got `0.18-0.31` withdrawn. It self-contradicts: 5 of the 8 clips where a
good lock WAS produced are marked "truth would not pass".
**The correct instrument already existed:** the neighbourhood sweep in
`data/output/court_scoring_diagnosis.md` §10 — a court a median 4.9 px from the clicks
clears the accept gate on **19 of 20** references (only `UHf0LeMU2pg` fails).
=> **the criteria do NOT bind; the search does.** I drafted "both stages are broken" and
retracted it in place. See [seen-frac-gate-positive-control](seen-frac-gate-positive-control.md)
for the same "check the checker" habit paying off.

## Prior art I should have found FIRST (cost me a wrong draft)

`eval/candidate_audit.py`'s docstring says **UNRUN — it is stale.** Session O ran it on
the 10 shell clips 2026-08-24: `data/output/court_scoring_diagnosis.md` §10 and
`docs/evidence/indoor-shell-courts.md`. **Before running any eval script in this repo,
grep `docs/evidence/` and `data/output/` for its numbers** — a docstring's own claim about
whether it has been run is not evidence (this is the T24 pattern again).
Shell then vs now: 3/10 -> 2/10 reached, 4 -> 5 locks-no-truth, 3 -> 3 no-lock. One clip
worse; two within-frame margins flipped sign. **Unconfirmed lead:** commit `4a33635`
scaled refiner reach 55 -> `55*w/640`, cleared as "no-op on the gate" — but shell is
3840x2160 (6x) and shell is NOT in the gate pool, so a shell-only effect was invisible to
its control.

## Population identity — three distinct 20/10-clip court pools, do not merge

1. `run_refs.references()` = 20 `data/*_pts.json` with `_exact:true` — 8 Hardcourt,
   2 Clay, 10 Shell (= 5 shell recordings x2 points). This is what I measured.
2. The **10 original calibrated clips** — researcher's `7/10 generated` comes from here
   (`docs/evidence/court-detection-frames-that-each-find-the.md`), NOT from my 20.
3. `data/gold/*.court.labels.json` (`am_*`) — a different pool again.
`HoHxFSX_gLk_s1/s2` share a source; the 10 shell clips are 5 recordings.
