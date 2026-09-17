---
name: calibration-trap-check-corners-first
description: A low fit residual does NOT mean a calibration is right — render the clicked corners and look, before trusting any clip's homography
metadata:
  type: feedback
---

**Render the clicked corners on frame 0 at 2× and LOOK, before trusting any
calibration.** Also treat an implausible camera height as a failure.

**Why:** `data/yt_match40_pts.json` is miscalibrated and the audit says PASS. All four
clicked corners lie on run-off asphalt, hedge and fence — no court line.
`tools/validate_new_clip.py --audit` reports 0.9 px residual because a residual only asks
whether four points form a plausible projective image of a court, and four arbitrary
points in a sane trapezoid do. Consequence: the net line lands 35–75 px low, so
`select_players_on_court` calls the NEAR player FAR, and P0-2 published that as a
far-player rate for the wrong person. Recorded as trap `T23`; the file is human ground
truth and was NOT edited (rule 9).

**How to apply:** `data/output/p0_3_calib_corners_yt_match40.png` is the pattern to copy.
Do this FIRST on any clip before any number derived from its homography is quoted.

**Both calibrated gold clips are LOW cameras.** `am_hard_utr` is 1.74 m (known);
`yt_match40` is ~5.4 m behind the baseline and under ~2.2 m high (from the pixels — the
far baseline is occluded by the net tape, which only happens below ~2.2 m). Neither has
a measurable far court. There is no broadcast-mount clip in the calibrated set.

Related: [[data-limits-far-end-contacts]], [[traps-this-project-paid-for]].
