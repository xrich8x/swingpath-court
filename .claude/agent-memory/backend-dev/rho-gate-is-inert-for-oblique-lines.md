---
name: rho-gate-is-inert-for-oblique-lines
description: eval/corr_attrib.py:_match_line gates on |rho| from the image ORIGIN - measured 2026-09-06 to accept right-sideline matches up to 316 px@640 off truth
metadata:
  type: project
---

`eval/corr_attrib.py:_match_line(n0, r0, lines, scale, ang_deg=6.0, rho640=8.0)` decides
"is this detected line the same as this projected court line" by comparing **rho, the
perpendicular distance from the IMAGE ORIGIN**, plus a 6 deg angle tolerance.

**Why it is nearly inert for long oblique lines:** rotating a line by 6 deg about a point
near the origin's foot barely changes rho, while moving the line by
`sin(6 deg) x (distance along it)` at the far end. Measured on 40 clips, 2026-09-06: the
rho gate accepted **right doubles sideline** "matches" sitting a **median 34.9 px@640 and
up to 316 px@640** from the truth segment, on 27/40 clips. Replacing it with the mean
perpendicular distance at the truth segment's two endpoints (same 6 deg, gate 12 px@640)
leaves only **18/40** matching.

**How to apply:** it is fine for near-horizontal lines close to the origin's row (near
baseline: identical 36/40 and identical 2.60 px median under both rules). It is not fine
for sidelines. Any per-line residual, survivor population or "the lines are there" claim
built on this matcher for **oblique** lines is looser than it reads - re-check before
quoting it. Recorded, not fixed. Related: [[rows-are-detectable-widths-are-not]],
[[court-fit-ceiling-is-the-lines]].
