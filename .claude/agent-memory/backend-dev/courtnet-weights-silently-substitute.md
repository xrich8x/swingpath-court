---
name: courtnet-weights-silently-substitute
description: detect_court_learned prefers courtnet_ft.pt over whatever you pass; two gate numbers (12/20 gold vs 2/20 references) are different populations, not a regression
metadata:
  type: project
---

Two traps that cost time on court work, both confirmed 2026-09-09.

**1. Asking for a checkpoint does not get you that checkpoint.**
`calibration.detect_court_learned(weights=X)` silently loads `courtnet_ft.pt` if it
sits beside `X`, and the model is cached in a module global so a second call with
different weights is a no-op. The only reliable override is the `COURTNET_WEIGHTS`
env var, set **before** the first call. `courtfit.resolved_courtnet_weights()` now
mirrors that order so a provenance stamp reads the resolution, not the request.
**Why:** `courtnet_ft.pt` is our fine-tune and 17 of 20 gold clips were in its
training pool - an eval that thinks it is scoring the upstream checkpoint and is
actually scoring the fine-tune is self-grading.
**How to apply:** any court-model eval sets `COURTNET_WEIGHTS` explicitly and prints
the resolved basename. `detect_court_learned` already prints
`[calibration] court model: <name>` - read it.

**2. "12 of 20" and "2 of 20" are DIFFERENT POPULATIONS, not a regression.**
- **gold** = `data/gold/frames/<clip>/` + human click labels, 20 clips, 640x360
  cached frames. Shipped baseline **12/20 accepted, median 8.1 px, 0 wrong**. This
  is the population the "shipped gate >=12/20" refers to. Run with
  `eval/run_eval.py --gold --all`.
- **references** = `data/<clip>_pts.json` with `_exact`, 20 clips, real videos at
  native resolution (shell is 3840x2160). Shipped baseline **2/20 accepted, shell
  0/10**. Run with `eval/run_refs.py` or `eval/proposer_ab.py`.
Both are human-clicked and both are legitimate; they overlap only partly and shell
is absent from gold. Documented in
`docs/evidence/scaling-the-court-refiner-s-reach-with.md` as
"gold 12/20 -> 12/20; references 2/20 -> 2/20; shell 0/10 -> 0/10".
**How to apply:** name the population in every court number you quote, and remember
that a change cleared as a no-op on **gold** has had **no shell control at all** -
shell is 6x the gold frame width, so any absolute pixel constant is untested there.
See [[upstream-courtnet-does-not-fire-on-amateur]] and [[traps-this-project-paid-for]].
