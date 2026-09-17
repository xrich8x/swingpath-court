# The net tape as an INDEPENDENT camera-height estimator — consistency check

**DELIVERABLE:** the per-clip table (tape-implied H vs fitted H, delta, delta %), the
verdict against the pre-registered bar, the per-clip DIRECTION analysis, a sanity check of
the estimator itself, and a plain statement of what would resolve any disagreement.

**NEITHER ESTIMATOR IS GROUND TRUTH.** The fitted height comes from the four clicked
doubles corners. The tape-implied height comes from the measured row of the white net tape
plus the assumption that the net is at regulation height (0.914 m at the centre strap).
Disagreement proves **at least one is wrong, not which**. Nothing here corrects a height;
no `data/*_pts*.json` was modified.

Pre-registered bar: `.claude/journals/lead.md` §"PRE-REGISTRATION — the net tape as an
INDEPENDENT camera-height estimator, 2026-09-05". Method reused:
`docs/evidence/net-anchor-qa-verification.md` §3 (qa: mean-brightness profile across
disjoint column ranges on a clean frame).

Tool: `tools/net_tape_height.py`. Raw output: `data/output/corner_audit/net_tape_height.json`.
Test: `backend/tests/test_net_tape_height.py`.

---

## VERDICT — one line

**AGREE, and the reason it agrees is the finding: this instrument is precision-limited, and
the three disagreements that prompted the brief are 2–6 px of tape row, not 13–33% of camera
height.** 15 clips yielded a confident tape row (bar wanted ≥ 6, so **not underpowered**);
**13 of 15 (86.7%) land within 10% of the fitted height**, against a bar of ≥ 2/3. Directions
are **8 positive / 7 negative, median +0.3%** — no systematic sign. Two clips fall outside:
`demo30` (+75.4%) and `L73ep7JHiJ4` (−22.3%), both isolated below.

**The pre-registered AGREE branch says "the fitted heights stand and this closes."** It
closes on the evidence the tape can carry, which is less than it looked: see "What the 10%
bar is worth in pixels".

---

## The estimator

For a pinhole at height `H`, a point `h` metres above the ground at the same depth images at

    row = horizon + (ground_row - horizon) * (H - h) / H

so, inverting, `H = h / (1 - (tape_row - horizon)/(ground_row - horizon))`, `h = 0.914 m`.
Confirmed against the shipped fit before use: on `A7vXlWIlyrI` the stamped
horizon/ground/tape rows (575.0 / 681.5 / 623.8) return **1.687 m** against the stamped
`camera_h_m` **1.69**. So the model side of this arithmetic is exactly the shipped
projection; the only new quantity is the **observed** tape row.

**The search is over HEIGHT, not over image rows.** Searching rows directly is wrong: under
perspective and camera roll the tape is a sloped, slightly curved line, so "row 522" is only
meaningful at one column. Instead, under the FITTED pose, projecting the net line at a *fake*
height `h'` lands exactly where the real 0.914 m tape would land if the true camera height
were `H = 0.914 * H_fitted / h'` (the row offset depends on `h` and `H` only through `h/H`).
A 1-D sweep over `h'` through `calibration.project_court_3d` therefore generates precisely
the family of candidate tape curves — right columns, right slope, right curvature — and the
response peak converts straight to a camera height. **Every clip sweeps the same H range
(0.90–12.0 m), so the search cannot be accused of having been aimed at its own clip's fitted
answer**, and the results confirm that: measured rows land from −20.9 px to +13.5 px away
from the modelled row.

## The automated tape-row measurement, and its pre-registered refusal rules

qa's method, with three changes each removing a way a single profile (or an eye) can be
fooled:

* **clean plate, not one frame** — per-pixel median of 7 frames spread over the first 600, so
  a player, ball or racquet standing on the net line cannot make the band. Sequential decode.
* **a bright-BAND matched filter**, `score = min(on − above, on − below)`, so a merely bright
  region (a sunlit far court above the net) cannot score: the tape must be brighter than
  **both** neighbourhoods. All windows scale by `frame_height/720`.
* **three disjoint column ranges** inside the central 50% of the net span, which must agree.
  Central-only keeps `h = 0.914` honest — a parabolic cord to 1.07 m at the posts is ≤ 0.75%
  higher at the edge of that window.

Refusal rules, **written into the journal before the sweep ran**:

| rule | refuses when |
| --- | --- |
| R1 | fewer than 3 usable column ranges, or < 20 on-frame sample points in one |
| R2 | peak band contrast < 4.0 grey levels |
| R3 | robust z of the peak over the whole sweep < 4.0 |
| R4 | a rival peak ≥ 5 px away scores > 0.75 of the best (ambiguous) |
| R5 | the three column ranges' peaks disagree by more than 3.0 px × `frame_height/720` |

**12 of 27 clips were refused.** A refusal is the correct answer here — the entire value of
this estimator is independence, and a confidently wrong row destroys it.

## Per-clip results — the 15 confident measurements

`drow` = measured tape row minus the row this calibration's own projection puts the tape at,
at the frame-centre column. `%/px` = how much the implied camera height moves per pixel of
tape row on that clip (`H² / (h · (ground_row − horizon))`).

| clip | frame | fitted H | tape H | Δ m | Δ % | dir | tape row | model row | drow px | %/px | z | rival | spread px |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| demo30 | 1280x720 | 1.375 | 2.412 | +1.037 | **+75.4** | + | 293.6 | 280.1 | +13.5 | 5.5 | 6.03 | -0.02 | 1.0 |
| L73ep7JHiJ4 | 1920x1080 | 2.888 | 2.245 | -0.643 | **-22.3** | − | 230.2 | 251.1 | -20.9 | 1.2 | 11.61 | 0.39 | 2.0 |
| flexi_joy_p07 | 3840x2160 | 1.361 | 1.255 | -0.106 | -7.8 | − | 885.2 | 896.2 | -11.0 | 0.7 | 4.53 | 0.48 | 4.5 |
| flexi_franz_p01 | 3840x2160 | 2.503 | 2.683 | +0.180 | +7.2 | + | 789.0 | 780.9 | +8.1 | 0.7 | 9.55 | 0.70 | 5.5 |
| mpc_tuesday_p07 | 3840x2160 | 2.813 | 2.618 | -0.195 | -6.9 | − | 908.8 | 921.3 | -12.5 | 0.7 | 10.78 | 0.56 | 5.0 |
| yt_match40 | 1280x720 | 1.641 | 1.752 | +0.111 | +6.7 | + | 293.8 | 291.9 | +1.9 | 3.2 | 5.86 | 0.15 | 0.5 |
| flexi_joy_p01 | 3840x2160 | 1.362 | 1.274 | -0.088 | -6.4 | − | 888.1 | 897.8 | -9.7 | 0.7 | 4.32 | 0.53 | 3.5 |
| sAjkpeRq4P4 | 1920x1080 | 3.329 | 3.508 | +0.179 | +5.4 | + | 437.8 | 437.5 | +0.3 | 1.9 | 4.12 | 0.39 | 2.0 |
| mpc_tuesday_p01 | 3840x2160 | 2.794 | 2.664 | -0.130 | -4.7 | − | 903.8 | 912.1 | -8.3 | 0.7 | 11.01 | 0.54 | 5.0 |
| flexi_franz_p07 | 3840x2160 | 2.509 | 2.625 | +0.116 | +4.6 | + | 791.5 | 786.1 | +5.4 | 0.7 | 12.12 | 0.63 | 8.5 |
| am_hard_utr | 1920x1080 | 1.743 | 1.678 | -0.065 | -3.7 | − | 528.0 | 530.5 | -2.5 | 1.8 | 7.85 | 0.18 | 2.0 |
| tc8CGFxyRE8 | 1920x1080 | 2.004 | 2.035 | +0.031 | +1.6 | + | 524.3 | 523.4 | +0.9 | 1.3 | 6.32 | 0.50 | 1.5 |
| hillsborough_p02 | 3840x2160 | 1.638 | 1.628 | -0.010 | -0.6 | − | 1136.5 | 1137.5 | -1.0 | 0.8 | 5.85 | 0.30 | 2.0 |
| e8T34KoJzOw_s2 | 1920x1080 | 1.757 | 1.767 | +0.010 | +0.5 | + | 569.1 | 568.8 | +0.3 | 1.8 | 9.02 | 0.19 | 2.0 |
| hillsborough_p08 | 3840x2160 | 1.632 | 1.637 | +0.005 | +0.3 | + | 1138.0 | 1137.8 | +0.2 | 0.9 | 4.45 | 0.22 | 2.0 |

### The 12 rejects, and what refused them (rule 10)

| clip | refusal | net-anchor flag (prior run) |
| --- | --- | --- |
| A7vXlWIlyrI | R3 z 2.4 | FLAG |
| bump_ntrp30 | R3 z 1.7 | FLAG |
| bump_ntrp30b | R3 z 1.6 | FLAG |
| CYqapSq5llo | R4 rival 0.95 — two equally good bands | FLAG |
| HoHxFSX_gLk_s1 | R3 z 1.9 | ok |
| HoHxFSX_gLk_s2 | R3 z 2.9 | FLAG |
| HoHxFSX_gLk_s3 | R2 contrast 0.9 grey levels | FLAG |
| mpc_mixed_p02 | R3 z 3.3 | ok |
| mpc_mixed_p08 | R3 z 3.95 (**near miss**) | FLAG |
| UHf0LeMU2pg | R5 spread 5.0 px (bar 4.5, **near miss**) | FLAG |
| uR5q2cSM6AY | R5 spread 9.5 px | FLAG |
| yt_rally2 | R3 z 3.2 | ok |
| court, yt_court | no video (same 2 as every prior sweep) | — |

Two observations from the rejects, neither of which changes the verdict:

1. **The refusals are not random with respect to the older net-anchor screen**: 8 of the 12
   refusals are on clips that screen FLAGged, and only 4 of the 15 measured clips are FLAGged.
   That is consistent with "when the projected net is nowhere near a real net, there is no
   band to lock on to" — but the net-anchor bars are themselves **failed and retained only as
   reported numbers** (`net-anchor-calibration-check.md`), so this is a co-occurrence, not
   corroboration.
2. **`yt_rally2`, a known-good calibration, is refused (z 3.2).** The estimator is not
   available on demand; it is available where a bright tape happens to be visible against
   both neighbourhoods. Refusal carries no verdict on the calibration.

Two near-misses (`mpc_mixed_p08` at z 3.95, `UHf0LeMU2pg` at 5.0 px spread) are recorded and
**left refused**. A failed bar stays failed and so does a refusal bar.

## Verdict against the pre-registered bar

| bar clause | required | measured | result |
| --- | --- | --- | --- |
| minimum n | ≥ 6 confident tape rows | **15** | not underpowered |
| AGREE | \|Δ\| ≤ 10% on ≥ 2/3 of clips | **13/15 = 86.7%** | **AGREE** |
| direction | report per clip | 8 `+`, 7 `−`, median **+0.3%** | mixed, no systematic sign |

**AGREE.** The pre-registered consequence is that the fitted heights stand and this closes.

## Direction analysis — mixed, and the mixing is informative

**8 positive, 7 negative. A sign test on 15 clips gives p = 1.0; the median deviation is
+0.3% and the median row offset is +0.2 px.** There is no systematic modelling bias in the
tape projection. Had the three briefed clips' pattern held (a consistent under-read), this
would have pointed at a modelling error in how height is projected; it does not.

But "mixed signs = measurement noise" is only half right here, and the corpus lets the halves
be separated. **Four courts appear twice** (two clips each, same camera, same mount):

| pair | Δ % clip A | Δ % clip B | agreement |
| --- | --- | --- | --- |
| flexi_joy p01 / p07 | -6.4 | -7.8 | 1.4 pp, same sign |
| flexi_franz p01 / p07 | +7.2 | +4.6 | 2.6 pp, same sign |
| mpc_tuesday p01 / p07 | -4.7 | -6.9 | 2.2 pp, same sign |
| hillsborough p02 / p08 | -0.6 | +0.3 | 0.9 pp, both ≈ 0 |

**The estimator is repeatable to ~1–3 percentage points within a camera**, and each pair
agrees in sign. So the scatter across the corpus is **not** per-frame measurement noise — it
is stable, court-specific, and of the size a real net installation varies by. A net strung
1–2 cm off regulation, or sagging at the centre strap, is exactly a few percent of 0.914 m
and is indistinguishable from a few percent of camera height. **That is the honest reading of
the mixed signs: the residual spread is dominated by the net, not by the calibration and not
by the pixel measurement** — on the 4K clips, where a pixel is worth only 0.7%.

## What the 10% bar is worth in pixels — the load-bearing caveat

Differentiating the estimator: `dH/drow = H² / (h · (ground_row − horizon))`. The 10% bar
therefore corresponds to a tape-row measurement accuracy of:

| clip | %/px | pixels of tape row = 10% of H |
| --- | --- | --- |
| yt_match40 (720p) | 3.2 | **3.1 px** |
| demo30 (720p) | 5.5 | **1.8 px** |
| am_hard_utr (1080p) | 1.8 | 5.6 px |
| sAjkpeRq4P4 (1080p) | 1.9 | 5.3 px |
| the 4K clips | 0.7–0.9 | 11–14 px |

**On a 720p clip the entire pre-registered bar is three pixels of tape row.** This is why the
three numbers that prompted the brief moved so much:

| clip | briefed tape H | briefed Δ | this run's tape H | this run's Δ | row difference |
| --- | --- | --- | --- | --- | --- |
| am_hard_utr | 1.52 | -12.8% | 1.678 | -3.7% | **6.0 px** (522 vs 528.0) |
| yt_match40 | 1.84 | +12.2% | 1.752 | +6.7% | **1.5 px** (295.3 vs 293.8) |
| sAjkpeRq4P4 | 2.22 | -33.3% | 3.508 | +5.4% | **~30 px** (407 vs 437.8) — see below |

Row 522 on `am_hard_utr` is *exactly* the row that yields 1.52 m. The −12.8% and the −3.7%
are the same object measured 6 px apart by two methods. **Nothing about the fitted height
changed; the instrument got sharper.**

## Estimator sanity check

**Asked for: on `yt_match40` post-re-click (residual 0.0 px, coverage 0.948, far player's
feet at 24.0 m), does the tape-implied height land near the fitted one?**

Yes, now. Fitted 1.641 m, tape-implied **1.752 m, +6.7%**, from a measured tape row of 293.8
against a modelled 291.9 — **1.9 px**, on the sharpest measurement in the corpus (z 5.86,
rival 0.15, the three column ranges agreeing to 0.5 px). The briefed +12.2% came from an
eyeball read of "~295". At 3.2%/px, 295 and 293.8 differ by 3.8% of camera height.

So, to answer the brief's three-way question directly: **the +12.2% indicted the tape
measurement, not the calibration and not the regulation-net assumption.** The residual +6.7%
is 1.9 px on a 60.6 px net-to-horizon span and is inside the noise this instrument has on a
720p frame.

**Synthetic recovery, before any of the above was believed.** `backend/tests/test_net_tape_height.py`
plants a bright band on a synthetic plate at the row the tape would occupy for a *known* camera
height, and requires the sweep to return that height to within 3%: passes at 1.40, 1.75 and
2.60 m on the same fixture camera (fitted 1.641 m), so the `h' -> H` conversion is not
inverted and is not echoing the fit. The refusal path is pinned too — a featureless frame
refuses, two equally good bands refuse as ambiguous, and a missing pose refuses at R0.
12 tests; 525/525 backend tests pass.

Three further checks that the instrument is not simply re-reporting the model:

* **It moves off the model when the image says so** — measured rows land −20.9 to +13.5 px
  from the modelled row across the corpus, and the two courts with the largest offsets are
  the two that fail the 10% bar.
* **It refuses.** 12 of 27, including a known-good calibration.
* **It is repeatable across clips from the same camera** (the four pairs above).

### The one place two independent measurements of the same tape still conflict — `sAjkpeRq4P4`

qa measured this clip's tape by hand at **row 406–409** across four disjoint column ranges
(`net-anchor-qa-verification.md` §3), 29–31 px above the modelled 437.5, and also found the
ground/base transition 22–25 px off. **This tool's matched filter locks at row 437.8 — within
0.3 px of the model** (z 4.12, the weakest accepted, rival 0.39 — so a secondary band *is*
present at 39% of the peak).

I cannot resolve this from here and am not going to paper over it: **two independent
brightness measurements of the same object on the same clip disagree by ~30 px, and the
clip's `+5.4%` row in the table above is conditional on mine being the right band.** If qa's
row is the tape, `sAjkpeRq4P4` is −33% and is the corpus's worst clip, not a passing one.
That flips one clip; at 13/15 it does not flip the verdict (12/15 = 80% still clears 2/3).
`sAjkpeRq4P4` was already open in `docs/DECISIONS_PENDING.md` pending a human eye on its
`_netanchor.png`; this adds a second, sharper reason to look, and a specific question:
**which row, 407 or 438, is the white tape?**

### The two clips outside the bar

* **`demo30`, +75.4%.** Fitted 1.375 m (the lowest mount in the repo; CLAUDE.md already says
  its speeds are never citable). The band found is 13.5 px *below* the modelled tape and only
  18 px above the projected net ground line, on a clip where the whole net spans 47.9 px from
  horizon to ground. At 5.5%/px this clip cannot support a 10% statement at all: **`demo30`
  is below this instrument's resolution and its +75.4% should be read as "unmeasurable", not
  as a 75% height error.** Its refusal rules did not catch that, which is a gap — an
  additional pre-registered floor on `(ground_row − horizon)` would have refused it. Not
  added retroactively.
* **`L73ep7JHiJ4`, −22.3%.** The opposite situation and the one genuinely interesting
  disagreement: 1080p, a 204 px horizon-to-ground span, only 1.2%/px, strong response
  (z 11.61), tight column agreement (2.0 px) — and the band sits **20.9 px above** the
  modelled tape. That is a real geometric disagreement, not a precision artifact. It is the
  single clip in the corpus where the tape evidence materially contradicts the corner fit and
  the measurement is strong enough to mean it.

## What would resolve the disagreement

The tape cannot arbitrate a calibration on its own — it has two unknowns (camera height, net
height) and one observation. Ranked by cost:

1. **A human eye on two frames — free, and it is the next step.** `sAjkpeRq4P4` (which row is
   the tape: 407 or 438?) and `L73ep7JHiJ4` (is the band 21 px above the projection the tape,
   or something else?). Both renders already exist under
   `data/output/corner_audit/*_netanchor.png`. This is a `qa`/founder task, not mine — it is
   a visual failure mode, which by CLAUDE.md's own rule makes any conclusion provisional
   until the frames are seen. **Two clips resolve both outliers in the table.**
2. **A second independent height feature on the same frames — cheap, and it breaks the
   two-unknowns problem.** The net POST tops are at 1.07 m and are *structurally* rigid: a
   post does not sag. `net_anchor_check.net_post_segments_3d()` already projects them, and
   `render_corner_audit --net-anchors` already draws them. Measuring a post-top row where the
   posts are in frame gives a height estimate that shares the camera-height unknown but
   *not* the sag unknown. Where post-top and tape-top heights agree, the net is regulation
   and the disagreement is the calibration; where they split, it is the net. The cost is one
   detector for a short vertical high-contrast segment, and the constraint is framing: posts
   are off-frame on most of the low wide mounts here.
3. **A physical measurement on any one court — decisive but needs a human with a tape
   measure.** Camera height and net centre height, on a court in the corpus, would convert
   this whole file from a consistency check into a calibrated one. It resolves one court, not
   the corpus.
4. **What will NOT resolve it: more clips.** n is not the limit — 15 is already 2.5× the
   pre-registered minimum, the pairs show the measurement is repeatable, and the residual
   spread is court-specific rather than random. Adding clips buys precision on a mean nobody
   needs.

**What must not happen:** no fitted height gets edited on the strength of the tape. Under
AGREE that was never on the table, and the pre-registration bars it explicitly.

## NOT ESTABLISHED THIS RUN

* **Which of the two conflicting brightness measurements on `sAjkpeRq4P4` is the tape.** Needs
  an eye. Its `+5.4%` is conditional.
* **What `L73ep7JHiJ4`'s band at row 230 actually is.** The strongest disagreement in the
  corpus and unexplained.
* **Whether the 12 refusals hide disagreements.** By construction they are unmeasured, and
  the correlation with the older (failed) net-anchor FLAG is a co-occurrence only.
* **Any net-sag measurement.** The pair-consistency argument says sag is the most likely
  source of the few-percent residual spread; nothing here measures sag.
* **A `(ground_row − horizon)` floor for refusal.** `demo30` shows one is needed; adding it
  after seeing the result would be moving a bar, so it is recorded, not applied.

---

## Post-hoc observation: `h_prime` explains both outliers, and it is NOT a bar

Read after the sweep, so this is an observation and explicitly **not** a filter retro-added to
the pre-registered bar. It is recorded because it points at a cheaper next step than a
tiebreaker.

The tool reports `h_prime_m` — the net height that *would* make the observed band consistent
with the **fitted** camera height. A regulation centre tape is **0.914 m**, so `h_prime` near
0.914 means "the band I locked onto behaves like a real net tape".

| clip | `h_prime` (3 groups) | vs 0.914 | delta % | `rival_frac` |
|---|---|---|---|---|
| `am_hard_utr` | 0.949 / 0.933 / 0.966 | **+2 to +6%** | −3.7 (agree) | 0.179 |
| `L73ep7JHiJ4` | 1.176 / 1.162 / 1.190 | **+27 to +30%** | −22.3 (outlier) | **0.387** |
| `demo30` | 0.521 / 0.507 / 0.492 | **−43 to −46%** | +75.4 (outlier) | −0.019 |

**Both outliers have an implausible `h_prime`, and the agreeing clip does not.** A band at
1.18 m is not a tennis net tape — it is above even the 1.07 m post height. A band at 0.50 m is
half a net. On `L73ep7JHiJ4` the `rival_frac` is also the highest in the corpus at 0.387,
meaning a strong competing band was present and the filter had a real choice to make.

**So the likely reading of both outliers is a mis-locked band, not a wrong calibration** —
the detector found the top of a windscreen, a fence rail, or a banner rather than the tape.
That is a much cheaper explanation than a 22% camera-height error, and it is testable.

**Why this is not turned into a refusal rule here.** Adding `0.7 < h_prime < 1.15` after seeing
which clips it would exclude is exactly the post-hoc threshold this project has been caught
doing twice this week — once on a close-race margin, once on a coverage floor. If it is worth
having, it gets pre-registered and run on clips not used above, with the same discipline the
`seen_frac` sweep was held to.

**What it does change now:** the two outliers should not be described as camera-height
disagreements until the band identity is settled, and `L73ep7JHiJ4` in particular should not be
called "the one genuine geometric disagreement" without that check. The honest label for both
is **band identity unconfirmed**.
