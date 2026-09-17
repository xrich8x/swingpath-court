---
name: camera-motion-vs-court-agreement
description: Measured 2026-09-09 — camera motion costs the court vote a real 24 px@640 of apparent inter-frame disagreement but rescues zero clips; the disagreement floor (~25 px@640) is identical on perfectly static clips
metadata:
  type: project
---

**Camera motion is a secondary term in court inter-frame disagreement.** Measured over the
20 `eval/run_refs` references, 8 scored frames each, `courtfit.auto_fit_frame` per frame,
ORB+RANSAC background compensation, `courtfit.consensus` re-invoked (not re-derived).

- High-motion clips (M_win >= 20 px@640, n=5): median pairwise disagreement 44.2 -> **26.4**
  px@640 after compensation, a **24.0 px** drop. Real, quantified, previously unmeasured.
- Low-motion clips (n=11): compensation is a **0.01 px no-op** and they still disagree by
  **24.8 px@640** — the same as the compensated high group. **The floor is motion-independent.**
  Four *motionless* 4K shell tripods disagree with themselves by 29.9–37.5 px@640.
- **1 of 16** measurable clips crosses the 20 px wrong-court line under compensation
  (`HoHxFSX_gLk_s2` 41.6 -> 15.7). **0 of 20 change acceptance.**
- Pre-registered verdicts: BAR1 **INDETERMINATE** (rho 0.474 vs a 0.60 bar; group gap 18.6
  vs a 20.0 bar — both in the dead band, not rounded). BAR2 **PARTIAL**. BAR3 width/zoom
  **LINKED but n=3**.
- **Width**: zoom fully explains the *excess* on the 3 zooming clips (16.4% -> 6.5%, onto the
  static baseline 7.1%) but **8 of 12 fully static clips still disagree >=5%** — so zoom does
  NOT explain STATE's "frames disagree about WIDTH" row. Far baseline is worse and equally
  motion-free (`hillsborough_p02` 93.9%).

**Two reusable lessons.**

1. **Yesterday's motion number was the wrong covariate and had to be re-measured.**
   Displacement vs *video frame 0* (the right quantity for audit-sheet frame choice) is not
   displacement *within the eval window* (the right quantity for the vote). `sAjkpeRq4P4` is
   80.4 px on the first and **3.6 px** on the second. Always re-derive the covariate for the
   question being asked; do not reuse a number because it has the same name. See
   [[corner-audit-frame-choice-risk]].
2. **Validate a fit harness against numbers it did not produce.** Mine matched the shipped
   `ai_court_audit` lock counts on all 9 clips exactly AND reproduced STATE row 196's
   classical-arm "References: 2/20" accepted. That is what let me trust a 4K shell clip
   disagreeing with itself by 37 px.

**Do not re-claim `AGREE_PX` as a discovery.** `AGREE_PX = 30.0` being raw-pixel and
unscaled (30 / 10.0 / 5.0 px@640 at 640/1920/3840) is already in
`docs/evidence/agree-px-is-6-tighter-on-4k.md`, including that normalising it admits two
wrong courts on the 1920 references. The pixel-space vote penalises **resolution**, not
motion. Grep `docs/evidence` before claiming a source-level finding — same lesson as
[[court-proposal-recall-search-binds]].

Evidence: `docs/evidence/camera-motion-vs-court-agreement.md`.
