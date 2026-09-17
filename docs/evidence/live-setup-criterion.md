# A live setup criterion: is the far baseline clear of the net tape?

> Evidence for the `live-setup-criterion` row in [../STATE.md](../STATE.md).
> Basis: [setup-envelope-net-occludes-far-baseline.md](setup-envelope-net-occludes-far-baseline.md)
> — that finding is taken as given here and is not re-derived.
> Built 2026-09-05 (backend-dev). Code: `backend/swingvision/calibration.py`
> (`net_tape_clearance`), tests `backend/tests/test_net_tape_clearance.py`,
> sweep `data/output/net_clearance_sweep.json`.

## THIS IS GUIDANCE, NOT A SIXTH GATE

Five autonomous accept/reject gates have failed on this project — coverage/centrality,
the camera-height screen, the net-anchor `band_ratio`/`dy` bars, the net-post detector,
and fitted hfov. **This is not a sixth.** It differs in kind:

- It is asked **before a calibration exists**, not after. It tells a user *where to put the
  phone*; it does not adjudicate somebody's footage.
- It returns **a margin in pixels and a sentence**, never a boolean refusal. `net_tape_clearance`
  has no accept/reject return value at all.
- Nothing in the pipeline refuses on it. In `framing_report` it can hold a setup back from
  `good` to `warn` — the same weight the existing `min_elevation` proxy already carried — and
  it **never produces `poor`**. `poor` remains reserved for "fewer than 3 corners in frame".
- It is cheap and stateless (pure geometry, no image content), so the app can run it on every
  preview frame while the user is still moving.

If a future caller turns this into a silent refusal, that is a change of kind, and this
section is the record that it was not built that way.

## The criterion

A tennis net is **0.914 m** at the centre strap. Project the top of the net tape and the far
baseline into the image and compare their rows:

```
margin = row(net tape at court x)  -  row(far baseline at the same x)
```

Rows increase downward, so **margin > 0 means the far baseline sits above the tape** and the
two lines are separable. **margin ≤ 0 means they overlap** — and then no gate, no detector and
no human eye can tell a court clicked on the far baseline from one clicked on the net.

`net_tape_clearance(H, img_wh)` returns `margin_px`, `margin_px_720` (normalised by
`720/frame_height`, per the project's pixel-scaling convention), `worst_margin_px_720`
(repeated at both doubles sidelines, where the net rises toward its 1.07 m posts and the
occlusion is worse), the level, and the message to display.

**It has no free parameter.** The horizontal field of view is not assumed — it is
self-calibrated from `H` itself via `focal_from_homography`, so the four corners the user
placed determine the whole answer. (My earlier finding that fitted hfov scatters by up to
29° across re-clicks of the same mount is click noise on a determined quantity, not a second
unknown; camera height, which is what the margin actually tracks, repeats to ≤ 0.12 m.)

**Reproduction check.** The implementation rebuilds the source finding's synthetic pinhole
(3 m back, 80° lens, 720p) to within 1 px at every row:

| mount | this code | the source doc |
|---|---|---|
| 1.40 m | −15.0 | −15.0 |
| 1.64 m | −9.5 | −9.5 |
| 2.00 m | −1.3 | −1.4 |
| 2.50 m | **+10.0** | +10.1 |
| 3.00 m | +21.2 | +21.4 |
| 4.00 m | +43.1 | +44.1 |

## Pre-registered bands

Written into `.claude/journals/backend-dev.md` **before the sweep was run**, and unchanged
after seeing it:

| level | margin (px @720p) |
|---|---|
| **good** | ≥ +10 |
| **marginal** | 0 < m < +10 |
| **poor** | ≤ 0 |

+10 px is taken verbatim from the source doc, which names 10 px as the comfortable clearance
and reports its own sweep in those terms. It is *not* read off the clip table — and as the
reproduction table shows, +10 px @720p **is** the doc's 2.50 m row. 0 px is the geometric
crossover. No fourth band was invented.

## Re-derived `min_elevation` vs the shipped 0.28

`framing_report`'s `min_elevation = 0.28` is a threshold on the **far/near baseline width
ratio**. Solving for the camera height at which the margin crosses each band, over standoff
2–5 m, lens 65–100°, and 720p/1080p, and reading off the width ratio there:

| condition | camera height | far/near width ratio |
|---|---|---|
| crossover (margin = 0) | 1.98–2.21 m (median **2.06**) | 0.088–0.189 (median **0.121**) |
| comfortable (+10 px @720p) | 2.28–2.98 m (median **2.55**) | 0.091–0.189 (median **0.126**) |

**So the derivation gives ≈ 0.12, and the shipped number is 0.28 — about 2.3× too strict.**
Inverting it: a far/near ratio of 0.28 corresponds to a camera **8.47–10.03 m up** (median
9.64 m) with **+73 to +216 px** of clearance. That is a broadcast tower. It is not a height
any phone user can reach, and the message the threshold prints ("clamp it to the fence
(~2.5 m)") advises a mount that would never satisfy it.

**But the larger finding is that no threshold on that ratio works at all**, so "0.28 is wrong
by 2.3×" understates the problem. Across the 28 real calibrations:

- **Spearman(far/near width ratio, margin) = +0.189.** Essentially no relationship.
- **Spearman(fitted camera height, margin) = +0.937.** Strong, as the geometry says it must be.

The ratio confounds height with standoff and lens. `HoHxFSX_gLk_s1` at a **1.71 m** mount has
ratio **0.262**; `L73ep7JHiJ4` at **2.89 m** has **0.215** — the lower camera scores *higher*.
The ratios of clips this criterion calls poor span **0.106–0.268** and of clips it calls good
span **0.190–0.649**: complete overlap. Setting the threshold to the derived 0.12 would pass
27 of 28 clips, **15 of which have overlapping lines**.

That is why the criterion **supplements rather than replaces** `min_elevation` in code: the
shipped 0.28 is left untouched (changing it is a behaviour change with no evidence that any
value of it helps), and the pixel margin is added alongside as the thing the ratio was
standing in for. A follow-up worth doing is deleting the ratio check entirely, but that is a
removal decision, not this run's.

## Every calibration we have

All 32 `data/*_pts*.json` files, deduplicated. `h_m` and the audit verdict are the existing
stamps, not recomputed. `m720` is the centre-line margin; `worst` adds the doubles sidelines.

| clip | h_m | far/near | m720 | worst | **level** | existing audit |
|---|---|---|---|---|---|---|
| `flexi_joy_p01_pts` | 1.36 | 0.248 | −19.6 | −26.3 | **poor** | LOW-CAMERA |
| `flexi_joy_p07_pts` | 1.36 | 0.236 | −18.4 | −25.0 | **poor** | LOW-CAMERA |
| `HoHxFSX_gLk_s1_pts` | 1.71 | 0.262 | −14.0 | −20.9 | **poor** | LOW-CAMERA |
| `hillsborough_p02_pts` | 1.64 | 0.268 | −13.5 | −19.5 | **poor** | LOW-CAMERA |
| `hillsborough_p08_pts` | 1.63 | 0.242 | −11.5 | −17.1 | **poor** | LOW-CAMERA |
| `HoHxFSX_gLk_s3_pts` | 1.60 | 0.208 | −11.3 | −18.0 | **poor** | LOW-CAMERA |
| `demo30_pts` | 1.38 | 0.106 | −10.2 | −15.1 | **poor** | LOW-CAMERA |
| `mpc_mixed_p02_pts` | 1.64 | 0.207 | −10.2 | −15.5 | **poor** | LOW-CAMERA |
| `mpc_mixed_p08_pts` | 1.63 | 0.206 | −10.1 | −15.6 | **poor** | LOW-CAMERA |
| `A7vXlWIlyrI_pts` | 1.69 | 0.199 | −10.0 | −15.7 | **poor** | LOW-CAMERA |
| `yt_match40_pts` | 1.64 | 0.190 | −8.9 | −14.1 | **poor** | LOW-CAMERA |
| `HoHxFSX_gLk_s2_pts` | 1.59 | 0.170 | −8.7 | −14.5 | **poor** | LOW-CAMERA |
| `am_hard_utr_pts` | 1.74 | 0.182 | −7.8 | −13.5 | **poor** | LOW-CAMERA |
| `e8T34KoJzOw_s2_pts` | 1.76 | 0.167 | −7.4 | −12.9 | **poor** | LOW-CAMERA |
| `CYqapSq5llo_pts` | 1.98 | 0.214 | −6.7 | −14.6 | **poor** | LOW-CAMERA |
| `tc8CGFxyRE8_pts` | 2.00 | 0.208 | −6.6 | −16.9 | **poor** | **PASS** |
| `flexi_franz_p07_pts` | 2.51 | 0.269 | +0.8 | −7.2 | marginal | PASS |
| `flexi_franz_p01_pts` | 2.50 | 0.263 | +1.1 | −6.3 | marginal | PASS |
| `yt_court_pts` | 2.42 | 0.228 | +1.6 | −6.7 | marginal | PASS |
| `mpc_tuesday_p01_pts` | 2.79 | 0.267 | +5.4 | −3.8 | marginal | PASS |
| `mpc_tuesday_p07_pts` | 2.81 | 0.272 | +5.4 | −3.8 | marginal | PASS |
| `eala_pts_auto` | 8.89 | 0.564 | +7.2 | −0.2 | marginal | PASS |
| `L73ep7JHiJ4_pts` | 2.89 | 0.215 | +12.0 | +5.8 | **good** | PASS |
| `uR5q2cSM6AY_pts` | 3.32 | 0.217 | +14.8 | +3.8 | **good** | PASS |
| `sAjkpeRq4P4_pts` | 3.33 | 0.233 | +16.1 | +10.2 | **good** | PASS |
| `yt_rally2_pts` | 3.31 | 0.190 | +18.2 | +13.1 | **good** | PASS |
| `UHf0LeMU2pg_pts` | 3.35 | 0.218 | +24.5 | +16.7 | **good** | PASS |
| `court_pts_refined` | 12.28 | 0.649 | +1341.6 | +1014.5 | **good** | PASS |

Four files already stamped DEGENERATE, listed separately because their quads are not real
camera views and their numbers mean nothing:

| clip | h_m | m720 | worst | level |
|---|---|---|---|---|
| `court_pts` | 14.62 | +1154.0 | +886.3 | good |
| `yt_court_pts_singles` | 3.33 | +71.4 | −57.8 | good (centre) but −57.8 at the sidelines |
| `yt_court_pts_refined` | 7.09 | −61.0 | −61.0 | poor |
| `yt_court_pts_doubles` | 3.78 | — | — | **no physical camera fits the quad** → returns `None` |

`yt_court_pts_doubles` is the graceful-degradation path working: `project_court_3d` cannot
recover a pose, so the criterion returns `None` and `framing_report` simply omits it rather
than guessing.

**Cross-check against the mounts the brief named:** all seven land on the predicted side.
`yt_match40` 1.64 m, `am_hard_utr` 1.74 m, `demo30` 1.38 m, `flexi_joy_p01` 1.36 m are all
**poor**; `L73ep7JHiJ4` 2.89 m, `UHf0LeMU2pg` 3.35 m, `sAjkpeRq4P4` 3.33 m are all **good**.

## How many existing clips it refuses

Stated plainly, and not tuned to avoid:

**Of the 28 non-degenerate calibrations, 16 (57%) have a net tape that overlaps their far
baseline, 6 (21%) are marginal, and only 6 (21%) are good.**

**Every single clip below 2.0 m of fitted camera height is poor. Every clip at or above
2.89 m is good. The band between is entirely marginal.** The empirical crossover in real
calibrations is therefore 2.0–2.9 m, sitting exactly on top of the 1.98–2.21 m geometric
crossover and the 2.28–2.98 m comfortable band derived independently above.

Three things follow, and none of them is that the criterion is miscalibrated:

1. **This is not a scoring of footage quality, it is a scoring of MOUNTS.** The margin is
   almost a pure function of camera height (ρ = +0.937). Sixteen clips were recorded from a
   standing tripod or a low fence rail, and the geometry says what it says.
2. **`tc8CGFxyRE8` is the one clip where this disagrees with an existing PASS stamp** at a
   height below crossover (2.00 m, −6.6 px). It is not evidence that the stamp is wrong — a
   clip below the crossover is *unconfirmable from a still frame*, which is a weaker claim
   than *miscalibrated*. Recorded, not fixed.
3. **The two clips nobody could settle are both in the poor set** (`yt_match40` −8.9,
   `am_hard_utr` −7.8), which is the point of the source finding: they are unsettleable
   because the information is absent, not because the labelling or the tooling failed.

It also means the gold set is **not a fair sample of the setups this criterion would produce
in the field**, because the criterion did not exist when they were recorded. Any future clip
collected with the live indicator running should land in the good band by construction — and
if it does not, that is a real finding about the indicator.

## Where it surfaces

- `calibration.net_tape_clearance(H, img_wh)` — the primitive. Stateless, image-free.
- `calibration.framing_report(...)` — new fields `clearance_px_720`, `clearance_level`, plus
  the message. Can hold `good` back to `warn`; never yields `poor`.
- `courtfit.setup_verdict(...)` — carried in the `angle` block beside height and hfov, which
  is where the user-facing grader keeps mount questions.
- `run.py check` — printed under `Setup`. **The argument parser is unchanged.**

Live example, `demo_30s.mp4`:

```
  Setup   [OVERLAP] far baseline vs net tape: -13 px (at 720p; positive = clear)
          The net tape and the far baseline OVERLAP in this view (the far baseline
          is 13 px BEHIND the tape), so they cannot be told apart. Raise the camera:
          a fence clamp at ~2.5 m clears it, a standing tripod at ~1.5 m does not.
```

Note that `run.py check` reads the **shape-locked** homography the pipeline actually uses
(1.49 m for `demo30`), not the raw stamped corners the sweep table used (1.38 m), so its
number differs by a few pixels. Both say OVERLAP. This is deliberate — trap T15, predict by
invoking rather than by re-deriving.

Test coverage is `backend/tests/test_net_tape_clearance.py`, 32 tests, including a
reproduction of the source finding's table to 1.5 px, the crossover bracketed to 1.9–2.3 m
across nine standoff/lens combinations, resolution-independence of the 720p normalisation,
and two tests that assert the criterion **cannot** produce a `poor` framing verdict. Full
suite 571/571 (was 539); no pre-existing test moved.

## Limits

- Ideal pinhole, flat court, no lens distortion. A phone 0.5× ultrawide has distortion this
  ignores, and that matters most at the frame edges — i.e. exactly where `worst_margin_px_720`
  is measured. Treat the sideline number as indicative.
- It reports when the two lines **overlap geometrically**, not when a person or a detector
  actually confuses them. The practical margin is wider than the geometric one, which is a
  reason the good band sits at +10 px rather than +1.
- The net is modelled as a straight line from post to centre strap. Real nets sag as a
  catenary and real nets are often slack, so the true tape sits at or *below* the model near
  the sidelines. The criterion is therefore slightly optimistic at the edges.
- It assumes the far baseline is in frame. If it is not, `framing_report`'s corner check is
  the thing that fires, and it fires first.
- **It does not retro-justify or retro-condemn any past number.** A poor clip is not thereby
  proven miscalibrated (rule 9: mislabels get recorded, not fixed).

## NOT ESTABLISHED THIS RUN

- **No live-preview measurement.** The criterion is cheap and stateless by construction, but
  its cost inside a real camera-preview loop on device has not been measured, and there is no
  on-device harness for it yet.
- **Whether `min_elevation` should be deleted.** The evidence here says it does not measure
  what it claims (ρ = +0.189) and that its shipped value implies a 9.6 m mount. Removing a
  shipped check is a behaviour change; it is filed to `docs/DECISIONS_PENDING.md`, not taken.
- **The distortion correction** for 0.5× ultrawide, which is the lens the framing guidance
  actively recommends.
- **No human has looked at a frame** to confirm that a clip at, say, +5 px of margin is in
  fact separable to the eye. The geometric crossover and the perceptual one are different
  numbers and only the first is measured here.
