---
name: rows-are-detectable-widths-are-not
description: Measured 2026-09-06 - court line ROWS are found to ~1-3 px@640 but WIDTHS are 12-45 px out, because a width is two intersections with oblique sidelines; also the cross-ratio that protects the far row
metadata:
  type: project
---

Measuring the four observables of the near-baseline+net camera solve
(`docs/evidence/near-line-detection-precision.md`, n=40 human-calibrated clips, shipped
detector, px@640):

| observable | median px@640 |
|---|---|
| near baseline ROW | **0.83** |
| net line ROW | 6.22 |
| near baseline WIDTH | **12.44** |
| WIDTH at the net | **44.63** |

**Why:** a row is read off a near-horizontal line directly. A width is the separation of
two **intersections with oblique sidelines**, where a sub-degree angle error is levered
into tens of pixels. Treating rows and widths as the same kind of measurement (i.i.d.
gaussian pixel noise on all four) is what made the Monte Carlo optimistic.

**How to apply:** never model "N px of line-detection noise" as if it applies equally to
rows and widths. Any geometry whose sensitivity runs through a WIDTH or a width RATIO is
sensitive to sideline ANGLE, and must be priced against sideline detection, not against
the whole-court 6.4 px figure. Related: [[court-fit-ceiling-is-the-lines]].

**Availability is worse than precision.** Match rates on the same 40 clips: near baseline
36/40, left sideline 38/40, net GROUND line 24/40, **right doubles sideline 18/40**. All
four coexist on only **10/40**. The binding constraint is a SIDELINE, not the net.

**Two facts worth reusing:**

- **The cross-ratio protects rows.** With two anchor rows pinned,
  `r_net - r_far = (r_near - r_net) * D/(D+23.77)`. That factor is 0.11-0.25 and
  compressive, so a **19.6% standoff error costs only ~4 px of far-baseline ROW**. The far
  WIDTH `f*W/(D+23.77)` inherits the standoff error in full (33 px@640). Quote the CORNER
  error (17.4 px@640), not the row - the shipped 8.1 px bar is a corner metric.
- **Camera HEIGHT is robust where standoff is not** - recovered to 0.02-0.16 m even with a
  40% standoff error. If the near-baseline+net solve has a use, it is mount-height
  estimation for the setup criterion, not calibration.
  Related: [[net-tape-clearance-is-the-setup-criterion]], [[net-ground-vs-net-tape]].
