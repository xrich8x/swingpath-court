---
name: net-ground-vs-net-tape
description: The net has TWO rows in every frame - ground z=0 (homography) and white tape z=0.914 (needs pose). Comparing them cost a wrong "calibration is broken" verdict.
metadata:
  type: project
---

A homography puts the net GROUND line (court-y 11.885, z = 0) in the image. The
white tape a human actually looks at is 0.914 m up (1.07 m at the posts) and
**necessarily images higher**. Comparing the two is apples to oranges and fails
on every CORRECT calibration.

The closed form, worth keeping: for a pinhole at height `H`, `(row − horizon) ∝
H / depth`, so a point `h` above the ground at the same depth scales that offset
by `(H − h) / H`. Tape row `= horizon + (ground_row − horizon) × (H − 0.914)/H`.
Projecting the tape properly needs `calibration.project_court_3d` with an hfov
from `courtfit.cam_fit_quad` — **never** the 70° default (mounts here run 60–91°).

**Why:** on 2026-09-05 the lead read `yt_match40`'s re-click as "still wrong,
far corners on the net" from a 30 px gap that was this height difference. The
calibration was correct (0.0 px residual, 1.64 m camera; predicted tape 291.9,
observed ~295 → ~3 px). The associated claim "a wrong court scored 0.944
coverage" was withdrawn and must not be cited.

**How to apply:** any time a check compares a projection to the net, state which
of the two rows it uses. `tools/net_anchor_check.py` reports `horizon_row`,
`net_ground_row` and `net_tape_row` together and colours the two lines
differently for exactly this reason. Related: [[court-fit-ceiling-is-the-lines]],
[[calibration-trap-check-corners-first]].

Also settled here: **net-band texture (`band_ratio`) is a FAILED instrument.**
Pre-registered bars `band_ratio < 1.5` and `|dy| > 0.5 × net px height` flagged
14 of 27 calibrations and **inverted** on the only pair with known truth — they
flagged the correct `yt_match40` (0.78) and passed the wrong `.bak` one (7.84).
Do not re-propose it without a different control strip; the near-side
"court surface" control picks up the net's shadow and the netting's own base.
Post constants now live in `court.py` (`X_LEFT_POST` −0.914, `X_RIGHT_POST`
11.884, plus singles sticks 0.456 / 10.514, which are INSIDE the alley).
