---
name: cp1-stage1-audit-pass-qualified
description: CP1 stage 1 (synthetic whole-court paint fit) audited 2026-09-17 — PASS QUALIFIED; no truth leak, bit-identical repro, but one dev=score pose, sigma on-grid, codec-bound far lines
metadata:
  type: project
---

CP1 stage 1 audit (docs/evidence/court-fit-cp1-qa.md): numbers reproduce bit-for-bit, and no truth
reaches the fitter. It is still only PASS QUALIFIED:
- the fitter was developed on the same single camera pose it is scored on;
- the render PSF σ grid sits inside the fitter's grid (a probe with σ off the grid cost a little);
- the far-baseline margin is ~1.4 cm and it is the codec that spends it;
- the tail puts 1% of trials over 5 cm.

**Why:** when one agent writes both the renderer and the fitter, the things they share and never declare
are the real risk, more than an explicit leak.

**How to apply:** when auditing stage 2 of CP1 (or any render-and-fit rig), check these first:
- is `cx` passed from the truth object (`rcam.cx`)? It becomes a leak in A9;
- is the stamp taken at the END of the run (git_sha inside stamp())?
- does the stamp dict carry a duplicate "seed" key?
- is the render cache keyed on the version string rather than the code? If so, re-render fresh and
  compare — the fresh render was identical last time;
- does the render parameter grid coincide with the fitter's search grid?

For wait handling, see [[background-wait-does-not-survive-ending-turn]]; this run polled in a foreground
loop.
