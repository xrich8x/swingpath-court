---
name: g9-and-g8-remediation-audit
description: 2026-09-22 audit of the G8 remediation + G9 — numbers reproduce, but the pyramid failure is the run-off brightness step (not the net tape) and G9's wrong locks are coherent flow outliers (not lag)
metadata:
  type: project
---

Audit of `0783ff0` / `c2d4537` / `a3f6a2a` (docs/evidence/court-camera3d.md, "QA AUDIT 2026-09-22").
Every published number reproduced. **Two of backend-dev's causal attributions were REFUTED.**

**1. The pyramid's CP1 bar-4 failure is the SURFACE/RUN-OFF STEP, not the net tape.** In CP1 the
tape is 12-14 px below the far baseline, outside a ±2.25 px window. With clutter OFF the true camera
still fails (frac 0.00-0.02 on trials 1-3). Noiseless, no clutter, no codec, lens on or off: the
far-baseline ridge sits +0.9/+1.0 px from truth, and all 4 OUTER lines are pulled inward (95 DN
court against 80 DN run-off). **The tracking sim has no run-off step**, so any far-line instrument
proven on the sim is unproven where the surround differs in brightness.

**2. G9's locked-but-wrong knock frames are NOT a one-frame lag.** The Kalman gain is about 1. The
raw `_pose_from` is already 35-62 cm out, and starting the solver from TRUTH lands on the same wrong
pose (the data prefer it). The cause is 27-34 coherent, same-sign (about -24 px) outliers on the LEFT
sidelines, on the knock frame only; the Cauchy loss down-weights them but does not reject them. The
check passes for three reasons: the far lines are unchecked; whole 23.77 m sidelines are pooled at
min_line_frac 0.5 (far half 0.21-0.55, pooled 0.60-0.77); and seed 500 is below the pixel tolerance
everywhere, so it **passes as whole_court even with far lines ON**. The wrong-pose rate is 6/6, the
catch is 1/6, and a naive outlier trim fixes 3/6 and sends 3/6 to 2 m.

**Also:**
- Bar 3's registered-window failure is SYSTEMATIC: the furthest-off segments are the ones dropped as
  "unseen".
- Lock claims are still forgeable by any block consistent with itself.
- The G8 bar-3 OFF-arm file is stamped far_lines TRUE, the reverse of the described bug.
- The G8R gate artifacts predate their "committed-before" commit but reproduce bit-exactly.

**Why it matters / how to apply:**
- When a builder names a cause ("the tape", "a lag"), run a one-variable control that REMOVES the
  cause before accepting it.
- Replicate a failing frame by monkeypatching the tracker in memory and capturing internals. Pair
  it with a "solve from truth" control to separate a data fault from a solver fault.
- Do not score remedies on seeds 500-505.

Related: [[g8-far-line-audit]], [[tracker-fixes-hold-on-held-out-seeds]].
