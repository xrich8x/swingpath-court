---
name: subpixel-renderer-and-boundary-degeneracy
description: CP1 (2026-09-17) - renderers must blur BEFORE pixel binning or sub-pixel lines lose position; a thin line on a colour boundary is degenerate with a boundary shift (kappa fix, ~1.3 cm per 5%)
metadata:
  type: project
---

Seeded whole-court paint fit (R1) PASSED CP1 stage 1 on every line (far baseline L p90 3.58 cm, codec
on; 0.93 cm codec off). Evidence: docs/evidence/court-fit-cp1.md. Four build traps cost most of the
session, and each silently biased the far lines by 0.01-0.25 px:

1. **PSF after pixel binning erases sub-pixel position.** A line narrower than a pixel renders
   identically anywhere inside its row. Blur first (smooth box(x)Gaussian kernel on jittered 1/16
   samples). Box on a coarse grid followed by a discrete Gaussian still leaves a 0.01 px kink dipole.
2. **A fixed supersample grid quantises horizontal edges** (1/16 px); jitter it.
3. **An undithered uint8 round on noise-free frames** is a structured ~0.3 DN error; controls that
   say "zero noise" need float frames.
4. **A thin paint band ON a surface/run-off boundary is first-order degenerate** with a boundary shift
   (apparent shift ~ paint area / step). Fix: kappa = paint / step measured on the wide near baseline,
   with the step basis oriented court-side = 1 (a sign bug hit the right-hand lines). The cost:
   **kappa +5% moves the far baseline ~1.3 cm.**

Also: projected paint edges are asymmetric about the centreline (intersect the station normal with
each edge); a crossing test at >=30 deg missed the far doubles sideline at 29.6 deg; and libx265 plain
ABR overshoots on short clips (use VBV).

**Why:** each looked like "R1 cannot do it" until the true-camera measurement isolated the renderer.
**How to apply:** for any sub-pixel synthetic test, first measure each line with the TRUE camera as
the prediction (bias should be <= 0.002 px), before trusting a fitted result. Stage 2 should add a
kappa-mismatch arm. Related: [[court-fit-ceiling-is-the-lines]], [[traps-this-project-paid-for]].
