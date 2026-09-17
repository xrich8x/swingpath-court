# The net POST as a rigid off-plane camera-height reference — BUILT, PRICED, and it FAILS its pre-registered bar

> **DELIVERABLE**: a net-post detector wired into an existing entry point, plus a
> per-clip table of fitted / tape-implied / post-implied camera heights, the
> instrument's pixel-sensitivity, every refusal with its reason, and the verdict
> against a bar pre-registered before the sweep ran.

> **This is a diagnostic NUMBER for the human who confirms a calibration at setup.
> It is NOT a gate.** Four autonomous accept/reject gates have failed in this family
> (`verify_court` coverage/centrality, the camera-height screen, `net_anchor_check`'s
> `band_ratio` and `dy`). This is not a fifth. Nothing here rejects a calibration,
> edits a calibration, or changes a fitted height.

## Headline

**The post's per-pixel sensitivity is 15% BETTER than the tape's, exactly as the
geometry predicts — and the instrument is still far worse, because it loses on ROW
PRECISION by roughly 7×, and precision is what dominates.** On the pre-registered bar
(|post − fitted| ≤ 10% on ≥ 2/3 of confident clips, n ≥ 6) the detector scores
**3 of 11 = 27%**. The bar was 67%. **FAILED**, and not marginally.

Worse than failing: **the detector is confidently wrong.** Four of its eleven confident
rows are off by **+261.7%, +94.0%, −69.1% and −45.8%**. That is precisely the outcome
the brief named as worse than no row at all.

**The post's supposed structural advantage — two rigid measurements per frame — does not
materialise.** Eight of the eleven confident clips rest on ONE post; the other post
refused. And where both posts DO score (11 clips), their same-frame disagreement has a
**median of 20.8% of camera height** — the instrument's own repeatability is twice the
bar it would be judged against.

**Verdict: DEMOTE. The net tape remains the only working off-plane reference.** The post
cannot presently resolve the tape's sag confound, because the post is the noisier of the
two by a wide margin. This is a well-priced negative, not a failure to build the thing.

## Why a post and not more tape (the hypothesis this run tested)

The net tape works (`net-tape-camera-height-consistency.md`: AGREE, 13/15 within 10%)
and is the only shipped check reading a point **off** the ground plane — which
`independent-calibration-references.md` establishes is the whole reason it caught what
every ground-plane statistic missed. But the tape has one confound it cannot resolve
from its own evidence: **a net sags.** Four courts appear twice in the tape corpus and
every pair agrees in sign to ≤ 2.6 pp, which reads as court-specific slack rather than
per-frame noise — but the tape alone cannot say whether a clip's disagreement is a slack
net or a wrong calibration.

**A post does not sag.** Rigid, regulation `NET_HEIGHT_POST = 1.07` m, at a known court
x. So a post measurement is off-plane like the tape and free of the tape's confound.

**Sag has a known sign, which is what would have made the comparison directional.** From
`row = horizon + (ground_row − horizon)(1 − h/H)` the estimator inverts to
`H_est = H_true · h_nominal / h_true`. A sagging net has true `h < 0.914` at the centre,
images at a LARGER row, so `H_est > H_true`.

> **Net sag can only make the tape read the camera HIGHER. It can never make it read
> LOW.** So `tape > post` is consistent with slack; `tape < post` is not.

That asymmetry is real and still holds — **but it is unusable at the post's measured
precision**, see "Post vs tape" below.

## Post visibility is not the limit (already measured, not re-derived)

Both posts project inside the frame on **27 of 28** calibrations; at least one on
**28 of 28** (`independent-calibration-references.md`, falsifier run 2026-09-05). The
qualitative "posts are frequently off-frame" claim in `net-anchor-calibration-check.md`
is wrong. Confirmed again here: the predicted post images **18–179 px tall** across the
corpus, and **P6 (resolvability, ≥ 10 px) never fired on any clip**. Framing and
resolution are not what killed this. Detection is.

## The pre-registered bar and refusal rules

Written into `.claude/journals/backend-dev.md` **before any detector code existed** and
before the sweep. Reproduced verbatim in intent; unchanged after the result.

**Measurand.** The image row of the post TOP (`z = 1.07`) at the predicted post column
(`X_LEFT_POST = −0.914` / `X_RIGHT_POST = 11.884`, `y = NET_Y`). Same `h'`
reparametrisation as the tape: sweep a fake height `h'`, project `(X_POST, NET_Y, h')`
under the FITTED pose, and the response peak converts to `H = 1.07 · H_fitted / h'`.
The post BASE is on `z = 0`, carries no off-plane information, and is never used in the
height — it is reported only for framing and for `post_px`.

**Signal.** `postness(h') = max( min(on−left, on−right), min(left−on, right−on) )` — a
bar differing from BOTH neighbours, sign-agnostic because a post is dark against sky and
light against a dark fence. Sampled on the local perpendicular to the projected post (a
post leans under perspective), with `net_tape_height`'s window widths rotated 90° and
scaled by `frame_height/720`. The TOP is a STEP, not a peak:
`R(h') = mean(postness just below) − mean(postness just above)` over a ±4 px scaled
window; the post top is the peak of `R`.

**Refusal rules** (P0–P6, reported not dropped, rule 10):

| Rule | Condition | Constant |
|---|---|---|
| P0 | no camera pose, or degenerate horizon-vs-net-ground rows | — |
| P1 | ≥ 60% of the swept grid on-frame, and the ± window at the peak fully on-frame | `MIN_GRID_FRAC 0.60` |
| P2 | peak edge response ≥ 4.0 grey levels | `MIN_EDGE 4.0` |
| P3 | robust z of the peak over the sweep ≥ 4.0 | `MIN_Z 4.0` |
| P4 | best rival peak ≥ 5 px away scores ≤ 0.75 of the best | `RIVAL_SEP_PX 5.0`, `RIVAL_FRAC 0.75` |
| P5 | if BOTH posts pass, implied heights must agree to ≤ 3.0 px × scale of top row | `MAX_SPREAD_PX 3.0` |
| P6 | predicted post pixel length ≥ 10 px, **ABSOLUTE not scaled** | `MIN_POST_PX 10.0` |

P2–P5 are the tape's own constants, unchanged, so the two instruments are judged by the
same strictness. P6 is new: an edge measured on a 6 px bar is not measurable at any
sensor resolution — this is the rule `demo30` (47.9 px net span, 5.5 %/px) should have
hit in the tape run and did not. Clip estimate = mean of passing posts; zero passing =
clip refused.

**BAR** (the tape's own, reused verbatim from `independent-calibration-references.md`
§"second falsifier"): AGREE if `|post-implied − fitted| ≤ 10%` of fitted on **≥ 2/3** of
confident clips, with **n ≥ 6** confident clips. Fewer than 6 confident = NO VERDICT.

**Search range** `H ∈ [0.90, 12.0]` m, copied from the tape tool. This is part of the
estimator's specification and was **not narrowed after seeing the result** — see
"The rejects" for why that matters and what it would have bought.

## Pricing the instrument: pixels per percent

`dH/drow = H² / (h · (ground_row − horizon))`. As a percentage of `H`:

> **%/px = 100 · H / (h · (ground_row − horizon))**

The post's `h = 1.07` against the tape's `h = 0.914`, at the same depth and therefore the
same `(ground − horizon)`, so **the post is `0.914/1.07 = 0.854×` the tape per pixel of
row error — 15% MORE precise per pixel.** Measured across the corpus:

| instrument | min %/px | median %/px | max %/px |
|---|---|---|---|
| **post** (`h = 1.07`) | 0.56 | **1.26** | 5.27 |
| **tape** (`h = 0.914`) | 0.66 | **1.48** | 6.17 |

At 720p on `yt_match40` the post is 2.53 %/px against the tape's 2.96 %/px. So the
tape's entire 10% bar is ~3.4 px of tape row there, and the post's would be ~4.0 px of
post-top row — a slightly wider pixel budget.

**And that is the whole of the post's advantage. It is spent immediately by the row
measurement, which is where the two instruments actually differ:**

| | tape | post |
|---|---|---|
| what is matched | a **long horizontal bright band**, 120 sampled columns in 3 disjoint groups that must agree | a **step at the end of a short bar**, one column, ±4 px of window either side |
| row estimate averages over | ~120 independent columns | ~16 grid samples of one column |
| measured row error (median) | 2–6 px (`net-tape-camera-height-consistency.md`) | **22.3 px** (this run, |peak − predicted|, n = 54 posts) |
| same-frame internal disagreement | 3 column groups within 3 px (R5) | **two posts median 20.8% of H**, range 1.7–134.5% |

> **The post wins sensitivity by 15% and loses row precision by roughly 7×.** Precision
> dominates. Priced honestly, the post is the WORSE instrument, and the cross-feed's
> question — can an off-plane rival beat the tape's 10% / 3.2 %-per-px benchmark — is
> answered **no**, for the second candidate in a row.

## Per-clip table: fitted / tape-implied / post-implied

`%/px` columns are this clip's own sensitivity; `post px` is the predicted post length
(left/right). `court` and `yt_court` have no video.

| clip | res | fitted | tape | tape Δ% | **post** | **post Δ%** | %/px post | %/px tape | post px | refusal |
|---|---|---|---|---|---|---|---|---|---|---|
| `A7vXlWIlyrI` | 1080p | 1.686 | — | — | — | — | 1.48 | 1.73 | 67.0/68.1 | P3 both (z 2.7, 2.4) |
| `am_hard_utr` | 1080p | 1.743 | 1.678 | −3.7 | — | — | 1.56 | 1.82 | 63.1/64.8 | P5 posts differ 46.9 px |
| `bump_ntrp30` | 298p | 3.734 | — | — | **1.155** | **−69.1** | 4.35 | 5.09 | 22.7/22.8 | — |
| `bump_ntrp30b` | 338p | 3.230 | — | — | — | — | 5.27 | 6.17 | 18.4/18.4 | P5 posts differ 4.0 px |
| `CYqapSq5llo` | 1080p | 1.980 | — | — | **3.841** | **+94.0** | 1.17 | 1.37 | 83.9/85.1 | — |
| `demo30` | 720p | 1.375 | 2.412 | +75.4 | — | — | 2.68 | 3.14 | 37.0/38.2 | P3 both (z 2.7, 3.4) |
| `e8T34KoJzOw_s2` | 1080p | 1.757 | 1.767 | +0.5 | — | — | 1.52 | 1.79 | 65.2/65.9 | P5 posts differ 15.1 px |
| `flexi_franz_p01` | 2160p | 2.503 | 2.683 | +7.2 | — | — | 0.56 | 0.66 | 177.5/174.2 | P3 both (z 3.7, 2.8) |
| `flexi_franz_p07` | 2160p | 2.509 | 2.625 | +4.6 | **9.073** | **+261.7** | 0.56 | 0.66 | 178.9/174.7 | — |
| `flexi_joy_p01` | 2160p | 1.362 | 1.274 | −6.4 | **1.781** | **+30.8** | 0.64 | 0.74 | 157.1/157.3 | — |
| `flexi_joy_p07` | 2160p | 1.361 | 1.255 | −7.8 | — | — | 0.67 | 0.78 | 150.2/150.1 | P3 both (z 3.6, 2.4) |
| `hillsborough_p02` | 2160p | 1.638 | 1.628 | −0.6 | — | — | 0.72 | 0.84 | 138.8/137.7 | P3 left, P2 right (3.1) |
| `hillsborough_p08` | 2160p | 1.632 | 1.637 | +0.3 | **1.634** | **+0.1** | 0.80 | 0.93 | 126.0/125.2 | (1 post; right P4) |
| `HoHxFSX_gLk_s1` | 1080p | 1.710 | — | — | — | — | 1.26 | 1.48 | 79.5/79.1 | P5 posts differ 51.2 px |
| `HoHxFSX_gLk_s2` | 1080p | 1.591 | — | — | — | — | 1.77 | 2.07 | 57.4/55.9 | P4 left, P3 right |
| `HoHxFSX_gLk_s3` | 1080p | 1.597 | — | — | — | — | 1.57 | 1.84 | 65.3/63.1 | P5 posts differ 11.5 px |
| `L73ep7JHiJ4` | 1080p | 2.888 | 2.245 | −22.3 | — | — | 1.32 | 1.55 | 73.8/73.0 | P5 posts differ 6.0 px |
| `mpc_mixed_p02` | 2160p | 1.636 | — | — | — | — | 0.81 | 0.95 | 121.0/125.6 | P3 both (z 3.5, 3.9) |
| `mpc_mixed_p08` | 2160p | 1.628 | — | — | **1.801** | **+10.6** | 0.82 | 0.96 | 119.6/124.6 | — (2 posts, 2.0 px) |
| `mpc_tuesday_p01` | 2160p | 2.794 | 2.664 | −4.7 | **2.798** | **+0.1** | 0.66 | 0.77 | 155.9/145.4 | (1 post; right P4) |
| `mpc_tuesday_p07` | 2160p | 2.813 | 2.618 | −6.9 | **3.341** | **+18.8** | 0.65 | 0.76 | 159.8/145.2 | (1 post; left P4) |
| `sAjkpeRq4P4` | 1080p | 3.329 | 3.508 | +5.4 | **4.219** | **+26.7** | 1.55 | 1.81 | 61.8/62.1 | (1 post; right P4) |
| `tc8CGFxyRE8` | 1080p | 2.004 | 2.035 | +1.6 | **2.109** | **+5.3** | 1.06 | 1.24 | 95.9/93.0 | (1 post; right P3) |
| `UHf0LeMU2pg` | 1080p | 3.349 | — | — | **1.816** | **−45.8** | 1.13 | 1.33 | 84.1/84.2 | — (2 posts, 2.1 px) |
| `uR5q2cSM6AY` | 1080p | 3.320 | — | — | — | — | 1.65 | 1.94 | 59.8/59.5 | P5 posts differ 78.4 px |
| `yt_match40` | 720p | 1.641 | 1.752 | +6.7 | — | — | 2.53 | 2.96 | 39.4/39.1 | P3 both (z 1.5, 2.8) |
| `yt_rally2` | 720p | 3.315 | — | — | — | — | 2.41 | 2.83 | 40.6/39.6 | P5 posts differ 55.8 px |

`|post Δ%|` over the 11 confident clips, sorted:
**0.1, 0.1, 5.3, 10.6, 18.8, 26.7, 30.8, 45.8, 69.1, 94.0, 261.7**.

## Verdict against the pre-registered bar

| | pre-registered | measured |
|---|---|---|
| confident clips | ≥ 6 | **11** ✔ |
| within 10% of fitted | ≥ 2/3 | **3/11 = 27.3%** ✘ |

> ### FAILED. A failed bar stays failed.
> The bar is not moved, and no threshold in the detector was changed after the sweep.

For contrast on the identical corpus and identical constants, the tape scored
**13/15 = 87%** confident-and-within-10%. The post scores 27%.

## The rejects — inspect what the filter threw away AND what it kept (rule 10)

**16 clips refused.** The refusal split is itself the finding:

| refusal | clips | what it means |
|---|---|---|
| **P3** robust z of the peak < 4.0 | 7 | no candidate post top stands out from the rest of the swept column at all |
| **P5** the two posts disagree | 8 | two rigid objects, same frame, implied heights differing by 4.0–78.4 px of top row |
| **P4** rival peak / **P2** contrast | 2 (as the *last* failing post) | ambiguous |
| **P6** resolvability | **0** | never fired — the post is always big enough |
| **P0/P1** framing / pose | **0** | never fired — framing is genuinely not the limit |

**And the kept rows are worse than the rejected ones.** Three mechanisms, each visible in
the data:

**1. Eight of eleven confident clips rest on ONE post.** `CYqapSq5llo`,
`flexi_franz_p07`, `flexi_joy_p01`, `hillsborough_p08`, `mpc_tuesday_p01`,
`mpc_tuesday_p07`, `sAjkpeRq4P4`, `tc8CGFxyRE8`. The redundancy that was supposed to be
the post's structural advantage over the tape is present on 3 clips out of 27.

**2. P5 passing is not protection, because the confuser is symmetric.** Of the 3 clips
where both posts passed and agreed, **2 are grossly wrong**: `bump_ntrp30` (both posts
peak at `h' ≈ 3.46` m, agreeing to 1.5 px, giving −69.1%) and `UHf0LeMU2pg` (both at
`h' ≈ 1.97` m, agreeing to 2.1 px, giving −45.8%). **A fence rail is horizontal and runs
behind BOTH posts at the same height**, so it produces the same step at the same `h'` on
both sides. The two-post cross-check is confounded by exactly the class of confuser it
was designed to catch. This is a structural objection to the post as an instrument, not
a tuning problem.

**3. Where the two posts agree well, they often agree on the same wrong thing; where they
disagree, they disagree enormously.** Two-post same-frame disagreement expressed as a
fraction of camera height, all 11 clips where both posts scored:
`1.7, 2.3, 6.4, 7.9, 18.0, 20.8, 22.9, 64.6, 73.2, 129.4, 134.5` %, **median 20.8%**.

**The diagnostic that explains all of it.** Post-hoc, never read by any rule: at the post
top the calibration itself predicts (`h' = 1.07`), the step response sits at a **median
56.6th percentile** of its own sweep — i.e. on a typical clip the real post top is an
utterly ordinary value of the response. Only **8 of 54** posts put the predicted top in
the top 5% of the response; **28 of 54** put it at or below the 60th percentile. The
winning peak lands a **median 22.3 px** away from the predicted top (only 4 of 54 within
0.5 px; 12 beyond 50 px).

> **A narrower search range would not have saved this.** The obvious post-hoc fix — cap
> the sweep near `h' ≈ 1.07` — is (a) choosing a parameter after seeing the result, which
> this project has been caught doing twice this week, and (b) **circular**: the range
> would be centred on the fitted height, so the estimator would be steered toward the
> very number it is supposed to check independently. A reference that only works when
> told roughly the answer is not an independent reference. Stated here so that nobody
> later proposes it as an improvement.

## Post vs tape: sag or calibration error

Seven clips are confident in **both** instruments. This was the whole point of the build.

| clip | fitted | tape (Δ%) | post (Δ%) | tape > post? |
|---|---|---|---|---|
| `hillsborough_p08` | 1.632 | 1.637 (+0.3) | 1.634 (+0.1) | ≈ equal |
| `mpc_tuesday_p01` | 2.794 | 2.664 (−4.7) | 2.798 (+0.1) | no |
| `tc8CGFxyRE8` | 2.004 | 2.035 (+1.6) | 2.109 (+5.3) | no |
| `mpc_tuesday_p07` | 2.813 | 2.618 (−6.9) | 3.341 (+18.8) | no |
| `sAjkpeRq4P4` | 3.329 | 3.508 (+5.4) | 4.219 (+26.7) | no |
| `flexi_joy_p01` | 1.362 | 1.274 (−6.4) | 1.781 (+30.8) | no |
| `flexi_franz_p07` | 2.509 | 2.625 (+4.6) | 9.073 (+261.7) | no |

**The post is further from the fitted height than the tape on 6 of 7, and by a lot.** The
sag test cannot be run: `tape > post` would indicate slack, and it holds on effectively
zero clips — but that tells us nothing about sag, because the post's own error (up to
+261.7%) swamps the few-percent effect being looked for. **The tape's sag confound
remains unresolved, and the post as built cannot resolve it.**

**The one asymmetry that survives, stated because the cross-feed asked for it.** The
tape's confound (sag) is one-directional and court-specific — it can only make the net
read HIGH, and four repeat courts agree in sign to ≤ 2.6 pp. A rigid post genuinely has
no equivalent one-directional confound, so **on BIAS the post would be the better
instrument if its variance were comparable.** It is not: median 20.8% same-frame
disagreement against a 10% bar. **A bias advantage you cannot see through the variance
is not an advantage.** The claim is not made.

## What this means for the ranking of off-plane references

`independent-calibration-references.md` ranked net posts **#1** and gravity/arc **#2**.
Both have now been priced against the tape's benchmark and both fall short:

| candidate | status | why |
|---|---|---|
| net tape (`h = 0.914`) | **SHIPPED, works** | 13/15 within 10%; median 2–6 px row error; one unresolved confound (sag) |
| **net post (`h = 1.07`)** | **BUILT, FAILED its bar (this doc)** | 3/11; 15% better per pixel, ~7× worse row precision; two-post redundancy confounded by horizontal fence rails |
| gravity / arc | **DO NOT BUILD** (researcher, 2026-09-05) | 8–15 usable frames at these mounts, ~±20% from pixel noise alone, drag biases by flight phase |

**Two well-priced negatives beat one unpriced positive.** The tape's 10% / ~3 %-per-px
benchmark now has two failed challengers, which raises confidence in the tape rather
than lowering it.

## Where it is wired

- **`tools/net_post_height.py`** — the detector and the standalone sweep. Writes
  `data/output/corner_audit/net_post_height.json` with every per-post number, every
  refusal reason, and the post-hoc diagnostics.
- **`tools/render_corner_audit.py --net-anchors --post-height`** — computes the
  post-implied height alongside the existing net-anchor render, prints it in the caption
  on `<tag>_netanchor.png`, and adds it to `net_index.json`. Off by default: it costs a
  second decode per clip for the clean plate.
- **`backend/tests/test_net_post_height.py`** — pins the geometry, the
  reparametrisation, the signal's sign-agnosticism and every refusal rule.

`run.py`'s argument parser is unchanged.

## What a human should take from this

**Do not put a post-implied height in front of a user.** On this corpus it would have
told them their 3.73 m camera was at 1.16 m, and their 2.51 m camera was at 9.07 m, with
no warning attached. The tape number already shipped is the one to show.

**If anyone revisits this**, the failure is localisation of a short vertical edge against
cluttered backgrounds, not geometry, not framing, and not resolution — P0, P1 and P6
never fired once across 27 clips. That is a detector problem, and this project's own
history (the ~6.4 px line-detector-to-truth ceiling that closed the classical court
branch) says the ceiling on classical vertical-edge localisation in this footage is
already known to be the binding constraint.

## NOT ESTABLISHED THIS RUN

- **Whether a better post detector exists.** This run tested one pre-registered
  detector — a sign-agnostic perpendicular band filter with a step-edge response — and
  it failed. That is evidence about this detector, not a proof that the post is
  unmeasurable. It is, however, enough to demote the candidate below the tape.
- **Whether the post-top confusers are in fact fence rails.** The mechanism is inferred
  from two posts locking to the same non-post `h'` (a horizontal structure spanning both
  posts is the parsimonious explanation) and from the peak's median 22.3 px offset. **No
  frames were examined by eye** — that needs a human look at the `_netanchor.png` renders
  for `bump_ntrp30` and `UHf0LeMU2pg`.
- **Anything about sag.** The instrument built to resolve it is too noisy to resolve it.
- **A `docs/STATE.md` row.** Out of scope for this run (`NOT-THIS-RUN`); the lead must
  add one. The number that moved: net-post reference **FAILS** its pre-registered bar at
  3/11 (bar 2/3, n ≥ 6), evidence `docs/evidence/net-post-detector.md`.
