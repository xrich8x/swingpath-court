---
name: net-tape-clearance-is-the-setup-criterion
description: The derived setup criterion (far baseline vs net tape, in px) replaces the guessed min_elevation=0.28; the width ratio is rho +0.189 against the thing it stands for, camera height is +0.937
metadata:
  type: project
---

`calibration.net_tape_clearance(H, img_wh)` measures, in pixels at 720p, whether the far
baseline sits clear of the top of the net tape. Positive = separable, `<= 0` = the two lines
OVERLAP and no verification of that view is possible. Shipped 2026-09-05 with 32 tests;
evidence `docs/evidence/live-setup-criterion.md`, sweep `data/output/net_clearance_sweep.json`.

**Why:** the source finding ([[mobile-port-split]]'s sibling,
`docs/evidence/setup-envelope-net-occludes-far-baseline.md`) showed a 0.914 m net projects
above the far baseline below ~2.0–2.2 m of mount height. That is why five verification gates
and three careful frame-reads failed — below the crossover the information is not in the
image. Framed and built as GUIDANCE, asked *before* a calibration exists, explicitly not a
sixth gate: no boolean refusal anywhere, and it cannot produce a `poor` framing verdict.

**How to apply:**

- **`min_elevation = 0.28` in `framing_report` is not merely mis-valued, it is the wrong
  instrument.** Over 28 real calibrations, Spearman(far/near width ratio, clearance) =
  **+0.189**; Spearman(fitted camera height, clearance) = **+0.937**. `HoHxFSX_gLk_s1` at
  1.71 m scores ratio 0.262 while `L73ep7JHiJ4` at 2.89 m scores 0.215 — the lower camera
  scores higher, because the ratio confounds height with standoff and lens. Poor and good
  clips overlap completely in ratio. Do not propose retuning it; the derivation's value is
  ~0.12, and 0.28 implies a 8.5–10.0 m mount. Deletion is filed in `DECISIONS_PENDING`.
- **Expect the criterion to refuse most of the gold set and do not read that as a bug.**
  16 of 28 (57%) OVERLAP, 6 marginal, 6 good. Every clip below 2.0 m is poor; every clip at
  or above 2.89 m is good. The gold set predates the criterion, so it is not a fair sample of
  what the criterion would produce in the field.
- **A poor clip is un-confirmable, NOT proven miscalibrated.** Weaker and different claim.
  See [[calibration-trap-check-corners-first]] and [[net-ground-vs-net-tape]] — both were
  cases of trying to settle a below-crossover clip from a still frame.
- **Self-calibrate the focal from H, never assume an hfov.** `focal_from_homography` makes
  the criterion parameter-free. My earlier hfov-scatter result is click noise on a determined
  quantity, not a second unknown — camera height repeats to <=0.12 m on the same mount.
- **Trap:** a `\n` inside an f-string written through a bash heredoc python script became a
  real newline and broke `run.py`. Use `print("")` rather than embedding `\n`.
