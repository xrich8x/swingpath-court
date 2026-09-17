---
name: composite-beats-its-members-but-fails-the-bar
description: The composite calibration score FAILS at 57% held-out (bar 80%) yet no solo signal matches it; coherence pairs save eala but exonerate the one real wrong calibration
metadata:
  type: project
---

The composite calibration score (`backend/swingvision/calib_score.py`,
`docs/evidence/composite-calibration-score.md`, 2026-09-06) **FAILS its pre-registered bar
on detection and MEETS it on false flags**: held-out 92/162 = **57%** (bar >=80%) at **1
false flag of 9** (bar <=1). `eala_pts_auto` scores **0.0** — the negative that broke two
previous screens is finally clean.

**Why the ensemble is nevertheless real (this is the finding worth keeping).** No solo
signal matches it. Held-out: best solo pooled is `residual` at 37% vs composite 57%; on
**depth compression** — the only corruption that matters — best solo is `lens_coherence` at
76% *and that member is the one producing the false flag*, vs composite **91%**. The
ablation the bar demanded as a kill-switch did not kill it.

**Coherence pairs are the mechanism.** A narrow lens is not wrong; a narrow lens on a LOW
mount is. A big net-tape clearance is not wrong; a big clearance next to a 1.7 m fitted
height is. Pairing two signals turned the failed 1-D hfov window into the composite's best
member without re-rejecting broadcast footage.

**The bill: the same coherence rule exonerates the ONE confirmed-wrong calibration.**
`yt_match40_pts.json.bak-2026-09-05` fits 10.82 m / 20.9 deg; `eala_auto` (correct,
broadcast) fits 8.73 m / 24.5 deg. Two metres and four degrees apart — the same camera to
five of six signals. Composite score **0.0, nothing fires**, pinned by
`test_the_one_real_wrong_calibration_is_MISSED_and_this_is_pinned`.

**Isotropic scale is 0/36 and argued unfixable.** Coverage catches it only relative to the
clip's own baseline; absolutely it overlaps believed-correct clips (0.188 / 0.326 / 0.433).
At setup time there is no baseline.

**Why:** the founder asked for a mix rather than the net alone, and the mix was principled
because the members fail for decorrelated reasons. The measurement backs the premise and
still misses the bar.

**How to apply:** do not propose a seventh solo gate, and do not retune this one to catch
the `.bak` — every constant that catches it re-breaks `eala`. The blocking need is **more
REAL wrong calibrations** (deliberate human mis-clicks, labelled), not more corruption
families: the synthetic positives are all low-mount amateur, and the one real failure was
high-mount-looking. Related: [[net-ground-vs-net-tape]],
[[net-tape-clearance-is-the-setup-criterion]], [[calibration-trap-check-corners-first]].
