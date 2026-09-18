---
name: photometric-lock-signal-separates
description: G7 measured it - an INDEPENDENT photometric read separates wrong 3D cameras from right ones (33/33 at 1 in 365), but the fit's OWN cost is INVERTED (AUC 0.216)
metadata:
  type: project
---

**A photometric cost separates a right 3D court camera from a wrong one — but only an
INDEPENDENT one. The paint fit's own robust cost is INVERTED.** Measured 2026-09-18,
pre-registered as G7 in `docs/evidence/court-camera3d.md`, 398 scored trials of arm K.

- `camera3d.paint_check(...).ok` at its **shipped defaults** caught **33 of 33** wrong cameras at
  **1 false flag in 365** — and that one flag was a mislabel, not a false positive. No new
  threshold was needed. `camera3d.paint_support` / a ridge-distance residual rank right above
  wrong on 96.8-99.7% of pairs.
- **The fit's own final robust cost has AUC 0.216: the WRONG camera holds the lower weighted cost
  in 78.4% of head-to-heads.** A wrong camera measures paint points on whatever lines it landed
  near and then fits them beautifully (median 0.018 px on ~950 points, vs 0.016 px for a right one).
- **A fraction alone is not enough.** One wrong camera at +132% focal scored `support` 1.000 by
  pushing most of the court out of frame; only `paint_check`'s `min_across` / `min_along` structure
  guard caught it. Any acceptance rule must also require that enough of the court was CHECKABLE.
- **The blind spot is total and was confirmed on all 398 trials:** the far baseline and far service
  line are too thin for the ridge finder at 3 m / 1080p, so `unchecked` always contained both.
  This family of instrument separates GROSSLY wrong cameras only — it says nothing about 5 cm.

**Why:** three roadmap items (multi-anchor selection, a Tier 2 acceptance rule, a "not locked"
re-localisation trigger) were written as if a photometric cost already did this, and nobody had
checked. Synthetic only: CP1 arm P, one camera pose, no players, no shadows, no worn paint.

**How to apply:** when anything needs to know whether the court is locked, reach for
`paint_check`, never for the optimiser's residual — and say which one you mean, because the two
answers are opposite. This is [[calibration-trap-check-corners-first]] and
[[court-fit-ceiling-is-the-lines]] in a third form: a fit's agreement with its own measurements
certifies nothing.
