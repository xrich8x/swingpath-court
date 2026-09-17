# The far-player MOTION gate: RESULT — **FAILS**

Execution of the gate pre-registered in
[far-player-motion-contrast-hypothesis.md](far-player-motion-contrast-hypothesis.md)
§"Pre-registered gate, before anything is built" (written 2026-08-29, before any code).
Run 2026-08-29 by backend-dev. **The bar was not touched.** Rule 2: a failed gate stays
failed.

> **Verdict: the nearest motion blob does NOT identify which blob is the far player.
> Median 5.751 box-heights against a bar of ≤1.5; 7 of 15 frames within 1.5 against a
> bar of ≥10 of 15. FAILS both halves. The null control also fails, so this is a clean
> negative and not the ambiguous "the control passed too" outcome. Per the pre-committed
> kill condition this joins `docs/STATE.md` "What has not worked" as the third measured
> negative in the player-foot-gate family, and per rule 3 the family is not to be
> re-proposed a fourth time.**
>
> **No eye is needed.** The stop condition in the brief is explicit: a nearest blob that
> is far away is far away regardless of what it is. No contact tiles were rendered —
> those were pre-committed to the PASS branch only.

## What every number here was measured against (rule 1)

**A POST-HOC far-player box taken from P0-3's `crop192@640_x` (yolo11x) pose detections
— a model-derived reference, not a human label.** It is the closest thing to a far-player
position that exists without new labelling, which is exactly why the gate chose it and
exactly why nothing below may be quoted as accuracy. The label travels with every number:
**POST-HOC**.

**No homography is touched anywhere in this run.** `movers.feet_in_court` and
`calibration.image_to_court` are never called. `yt_match40`'s calibration is confirmed
wrong (T23), so a near/far claim routed through it would be worthless; this experiment is
homography-free by construction and the gate doc's own compliance note is satisfied.

**Rule 5 note on what reaches the rendered output:** nothing does. This is an
intermediate-signal probe of a proposal that was never built. The only thing a pass would
have licensed was a crop-centring proposal feeding the existing `crop192@640` pose pass;
it did not pass, so no rendered-output number exists or was claimed.

## Method, exactly as specified

| Item | Value |
| --- | --- |
| Population | `yt_match40` far-end contacts where `crop192@640_x` found a far-sized non-near person — **15 of 25** |
| Selection rule | reproduced from `tools/p0_3_tolerance_sweep.py`: nearest `small_enough & not_the_near_player` candidate by box-edge distance to `ball_px_at_contact` |
| Method | `eval/movers.py` **unmodified**, `foot_points` as written (`WORK_W=960`, `PLATE_MAX=31`, `MAX_PLAYERS=4`) |
| Temporal window | 31 frames centred on the contact frame — exactly one `clean_plate` with no subsampling |
| Metric | distance from the **nearest** returned foot point to the POST-HOC far-player box centroid, in box-heights |
| Bar | median ≤ 1.5 box-heights on ≥ 10 of 15 frames, **and** the random-blob control fails the same bar |
| Seed | `--seed 0` on both arms (rule 7) |
| Runner | `eval/far_player_motion_gate.py` |
| Artifact | `data/output/far_player_motion_gate.json` |

### A discrepancy in the gate doc's population, recorded not silently resolved

The gate says *"the **15** of 25 contacts … within **1.5 box-heights** of the ball
anchor"*. Those are two different sets in `data/output/p0_3_tolerance_sweep.json`
(`yt_match40.mp4/arms/crop192@640_x`):

```
far_sized_candidate_found_anywhere_in_crop = 15      <- the "15"
by_rel_box_h["1.5"]                        = 14      <- the "within 1.5 box-heights"
by_rel_box_h["2.0"]                        = 15
```

The bar's own denominator is written "≥10 of **15**", so the found-anywhere set is
primary. **The 14-frame ≤1.5-anchor subset is reported alongside and it fails harder**
(median 6.396, 6 within), so the verdict does not hinge on the reading.

## Result

| Arm | median (box-heights) | within 1.5 | bar | verdict |
| --- | --- | --- | --- | --- |
| **Nearest blob** (the hypothesis) | **5.751** | **7 / 15** | ≤1.5 and ≥10/15 | **FAIL, both halves** |
| **Random blob** (null control, seed 0) | **9.265** | **2 / 15** | same | **FAIL** |
| Nearest, ≤1.5-anchor subset (n=14) | 6.396 | 6 / 14 | — | fails |

**Null-control stability (descriptive):** over 1,000 further seeded draws the control's
median-of-medians is 9.265 (p5–p95 8.11–9.919), mean 2.99 frames within 1.5, and
**0.0% of draws clear the bar**. The control is not a fluke of seed 0.

**The control is clean, and that matters.** The gate's whole design worry was that with
~9 blobs per frame "some blob is close" would be guaranteed by chance. It is not: random
fails decisively. So the nearest-blob number is a real measurement of the hypothesis and
not an artefact of candidate density — the hypothesis simply misses the bar by ~3.8× on
the median.

### The failure is BIMODAL, not marginal

Sorted nearest-blob distances, in box-heights:

```
0.21  0.24  0.27  0.28  0.28  0.30  0.62  |  5.75  7.04  8.11  10.12  11.81  11.87  18.77  25.16
```

**There is nothing between 0.62 and 5.75.** On 7 of 15 contacts the nearest foot point is
essentially *on* the far player (7–23 px, on boxes 23–39 px tall). On the other 8 it is
173–632 px away — in a 1280-wide frame, up to half the image. The mechanism does not
degrade gracefully; it is either right or it is looking at something else entirely
(the near player, or clutter). A crop centred on the 8 failures would be centred on the
wrong half of the court.

### The confuser census does not describe this population — and the negative survives it

`movers.py`'s comment reports a **median ~9 candidate blobs per frame (up to 18)** on the
20 gold clips. That is the count *before* `MAX_PLAYERS = 4` caps it. On these 15 frames the
post-cap field is much thinner: **median 2 blobs per contact frame (min 1, max 4, mean
2.53)**, from a median 68 foot points per 31-frame window. A thinner field makes the null
control *weaker* as a discriminator — a random draw is picking 1-in-2.5, not 1-in-9 — and
random still failed 2/15. On 6 of 15 frames the random draw happened to pick the nearest
blob outright. So the negative is not rescued by arguing the control was too easy; it was
harder than the gate anticipated and the hypothesis still lost.

## The contrast rider — DESCRIPTIVE CHARACTERISATION, NO GATE, PASSES AND FAILS NOTHING

**There is no pre-registered bar for contrast, because nobody has ever measured it on this
footage.** Inventing one after seeing these numbers would be a rule-2 violation. This
section is characterisation of how often the founder's premise holds, and it is not
permitted to conclude anything else.

Same 15 frames, same POST-HOC boxes. CIELAB (L\* on 0–100), player box against the ring
of court around it (the box grown by 1.0 box-height, minus the box).

| Statistic | min | p25 | median | p75 | max |
| --- | --- | --- | --- | --- | --- |
| \|ΔL\| (luminance) | 0.11 | 3.98 | **5.96** | 9.57 | 13.30 |
| Δchroma (a\*b\* plane) | 6.04 | 9.96 | **11.71** | 15.16 | 25.28 |
| ΔE (full Lab) | 6.32 | 11.13 | **14.67** | 17.95 | 25.71 |
| surround's own SD of L\* | 19.16 | 19.95 | **20.99** | 22.84 | 23.86 |
| \|ΔL\| ÷ surround SD of L\* | 0.01 | 0.17 | **0.30** | 0.43 | 0.59 |

What the distribution says, and no more:

- **The far player's luminance offset is consistently smaller than the court patch's own
  luminance spread.** The ratio never reaches 1.0 on any of the 15 frames; its median is
  0.30. Against brightness alone the player is a weaker signal than the background's own
  variation.
- **Colour is the stronger of the two channels here.** Δchroma has a floor of 6.04 and a
  median of 11.71, and it never collapses to zero the way \|ΔL\| does. The one frame where
  the player is essentially invisible in brightness (shot 145, \|ΔL\| = 0.11) still carries
  Δchroma 10.30.
- **The founder's premise is neither uniformly true nor uniformly false on this clip** —
  it spans \|ΔL\| 0.11 to 13.30 and ΔE 6.32 to 25.71 within a single recording. That
  matches, and now quantifies, P0-3's qualitative "sometimes a red shirt against dark
  hedge and sometimes near-silhouette".
- **Contrast does not separate the frames motion found from the frames it missed**, on
  this n: found vs missed medians are \|ΔL\| 5.96 vs 5.52, Δchroma 11.46 vs 12.05, ΔE
  15.93 vs 14.34, ratio 0.30 vs 0.28. n = 15 makes that characterisation, not a test — but
  it is the opposite of what "the failures are the low-contrast ones" would predict, so it
  should not be assumed without measuring.

## Two facts recorded for whoever scopes the next mobile build

1. **`eval/movers.py` lives in `eval/`, NOT in the shipped package.** The
   [mobile-viability audit](mobile-viability-audit.md)'s finding that *"every cv2 symbol
   the pipeline uses exists in OpenCV's iOS build"* covers `backend/swingvision/` only and
   **does not cover this module**. Its calls (`absdiff`, `GaussianBlur`, `morphologyEx`,
   `connectedComponentsWithStats`, `cvtColor`, `resize`) are standard core-OpenCV and the
   risk is judged low — but that is a judgement, not a re-run of the audit. **Re-checking
   it is a prerequisite line item before any build, not a footnote.** Not done this run,
   and moot unless something revives this module.
2. **`clean_plate` needs a rolling buffer of up to `PLATE_MAX = 31` frames.** Harmless for
   the shipped record-then-process design — the clip is already in hand. **Fatal for any
   live/real-time use**, where it would be rebuilt, not ported.

## Reproduce

```bash
./backend/.venv/Scripts/python.exe eval/far_player_motion_gate.py \
    --probe data/output/p0_3_probe_yt_match40.json \
    --video data/incoming/Hardcourt/yt_match40.mp4 \
    --arm crop192@640_x --seed 0 \
    --out data/output/far_player_motion_gate.json
./backend/.venv/Scripts/python.exe -m pytest backend/tests/test_far_player_motion_gate.py
```

CPU only, no GPU, no inference, no new labelling. `backend/tests/test_far_player_motion_gate.py`
(11 tests) pins the population-selection rule against `tools/p0_3_tolerance_sweep.py`'s own
`_edge_dist`, pins the three bar constants so a later edit cannot quietly move them, and
pins `movers`' constants so a silent retune cannot masquerade as the same run. Full suite:
479 passed.

## T24 again: `eval/movers.py`'s docstring still says "UNRUN"

It still opens with *"UNRUN. Written 2026-08-24 ... no number in this repo has been
measured with it yet."* That is now wrong for the **third** time — its primitives ran
2026-08-24 (`eval/candidate_audit.py --movers`, `eval/foot_gate_power.py`, 30 clips) and
`foot_points` ran again here. **The file was deliberately left byte-identical**, because
the gate specified `eval/movers.py` *unmodified* and the run artifact stamps
`movers_modified: false` alongside every one of its constants; editing it after the fact
would make that stamp disagree with the file on disk. Correcting the header is a one-line
job for whoever next touches the module.

T24's secondary complaint was that the STATE rows carrying `movers` results do not say
"movers" in their titles, so reading the table was not enough either. Both rows added
today name `movers.foot_points` explicitly, so a grep for the module now finds them.

Run history for this module, established the way T24 requires — from `git log`, from what
imports it, and from STATE, never from the prose inside it:

```
git log --oneline -- eval/movers.py   -> 424ecdc "The court diagnosis harness, and the
                                          twelve negatives it produced"; 733565a (a docs move)
imports                               -> eval/candidate_audit.py:222
docs/STATE.md                         -> the crop_row row, the two player-foot-gate rows,
                                          and now the two added today
```
