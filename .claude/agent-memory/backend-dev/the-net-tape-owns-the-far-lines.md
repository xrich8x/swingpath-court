---
name: the-net-tape-owns-the-far-lines
description: Any far-line measurement on a low mount competes with the net tape, which is ~5 px away and 10x brighter than 0.2 px of paint; clutter beat the lens by 250x
metadata:
  type: project
---

**On a low mount the far lines are not faint, they are OCCUPIED.** Measured G8, 2026-09-19,
CP1's renderer, 1080p, 3 m mount, 6 m setback, TRUE camera, one variable per arm:

| arm | far service stacked offset | stacked amplitude |
|---|---|---|
| no lens, no clutter | **+0.09 px** | 14.8 DN |
| lens distortion only | **+0.00 to +0.02 px** | 15.8 DN |
| clutter only | **-4.83 to -5.56 px** | **110 DN** |

The far baseline goes from 5.8 DN (real paint, detectable) to **68.6 DN with no paint ridge at
all**. The net tape projects about 5 px from the far service line and across the far baseline,
and it is an order of magnitude brighter than 0.2 px of paint, so any "nearest significant
ridge" rule takes the net. Consequence: a far-line check that scored 0.9167 catch at 0.0000
false flags on a clean court flagged **369 of 369 right cameras** on the cluttered one.

**Why:** the route notes had already listed "net tape near the far baseline on low mounts" as a
surviving bias; this is the first time it was measured on an instrument rather than argued, and
it is 250x larger than the lens distortion everyone expects to be the problem.

**How to apply:** (1) never conclude that a far-line algorithm works from a clutter-free arm —
run the clutter arm before quoting anything; (2) `calibration.net_tape_clearance` already
computes the px margin between the far baseline and the net tape with no image content and no
parameters, and **16 of 28 real calibrations OVERLAP**, so it is the right gate for whether a
far-line measurement is admissible at all; (3) suspect the confuser, not the optics, when a
sub-pixel measurement is metres out — see also [[net-ground-vs-net-tape]] and
[[calibration-trap-check-corners-first]].
