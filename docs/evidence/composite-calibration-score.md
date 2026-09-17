# A COMPOSITE calibration score: mixing every signal we built

> backend-dev, 2026-09-05/06. Scoped from the lead's pre-registration
> ("PRE-REGISTRATION — a COMPOSITE calibration score", `.claude/journals/lead.md`) and the
> founder instruction *"Don't just use the net — it should be a mix of all we've worked on."*
> **Read-only on ground truth:** no `data/*_pts*.json` was written to. Every corruption is an
> in-memory copy of the loaded corner dict. qa is evaluating this independently in
> `docs/evidence/composite-score-qa.md`; this file is mine and did not read theirs.
>
> Code: `backend/swingvision/calib_score.py`, tests `backend/tests/test_calib_score.py` (15).
> Raw numbers: `data/output/composite_signal_sweep.json` — 27 calibrations × 19 variants
> (baseline + 18 corruptions) = **513 rows**, each with 11 signals.
>
> **This is NOT a sixth gate.** Five accept/reject gates have failed on this project. The
> output here is a **score plus a reason string** for the human confirming setup. Whether it
> ever gates anything is a founder call, not this run's.

## Verdict, upfront

**The composite FAILS the pre-registered bar, and it fails on the half of the bar nobody
was worried about.**

On the held-out split it flags **57%** of synthetic corruptions (bar: ≥80%) at **1 false
flag among 9 believed-correct calibrations** (bar: ≤1 — **met**). `eala_pts_auto`, which
broke two previous screens, scores **0.0 and is not flagged**.

Three things that are worth more than the verdict:

1. **The mix is real, not redundant.** No solo signal comes close to the composite. On
   held-out, the best solo is `residual` at 37% pooled; the composite is 57%. On **depth
   compression — the corruption every shipped gate is blind to and the only one that
   matters** — the best solo is `lens_coherence` at 76% *while false-flagging a correct
   clip*; the composite is **91% with that clip as its only false flag**. The ablation the
   bar demanded as a kill-switch does **not** kill the ensemble.
2. **The failure is concentrated and diagnosable: isotropic scale, 0/36.** Not "the mix is
   weak" — a specific, explained blind spot (below).
3. **The composite scores 0.0 on the ONE confirmed-wrong calibration this project has.**
   It is not a near miss; nothing fires. The reason is measured and is the most useful
   sentence in this document (below).

## The pre-registered bar (lead's, unchanged, not retuned)

- Choose the combination rule on a **TRAIN** split of clips; report on a **HELD-OUT** split.
- **PASS** = on held-out clips, flags **≥ 80%** of synthetic corruptions at **≤ 1 false
  flag** among the calibrations believed correct, with **`eala_pts_auto` included as a
  negative**.
- **FAIL** = anything else. A sixth failure is a fine outcome.
- **Mandatory ablation:** each signal's SOLO score beside the composite. If one signal alone
  matches the composite, say so plainly — that kills the ensemble.
- **Report by corruption TYPE, never pooled.** Depth compression is the one that matters.

## The train / held-out split

Split declared and computed **before any result was inspected**, seeded and reproducible:

```
TRAIN  iff  sha256("calibsplit-seed-2026-09-05|" + tag)  is even
```

| | clips | tags |
|---|---|---|
| **TRAIN** | 17 | A7vXlWIlyrI, CYqapSq5llo, HoHxFSX_gLk_s1/s2/s3, L73ep7JHiJ4, UHf0LeMU2pg, e8T34KoJzOw_s2, flexi_joy_p01, hillsborough_p02, mpc_mixed_p02/p08, mpc_tuesday_p07, sAjkpeRq4P4, tc8CGFxyRE8, yt_match40, yt_rally2 |
| **HELD-OUT** | 9 | am_hard_utr, demo30, **eala_auto**, flexi_franz_p01, flexi_franz_p07, flexi_joy_p07, hillsborough_p08, mpc_tuesday_p01, uR5q2cSM6AY |
| **known-WRONG** | 1 | `yt_match40_pts.json.bak-2026-09-05` — in neither split, reported alone |

The seed put `eala_auto` in HELD-OUT by luck, which is the best place for it: the negative
that broke two previous screens was never seen while the rule was being chosen.

Four `data/*_pts*.json` files (`court_pts*`, `yt_court_pts*`) have no video in the repo and
could not be scored — `coverage` needs a real frame.

**The positive class is synthetic, and that is a real limitation, stated up front.** There
is exactly **one** confirmed-wrong calibration in this project. You cannot fit or validate
an ensemble on n=1, so the positives are qa's five corruption families
(`docs/evidence/ground-plane-blindness-test.md`), reproduced here: depth compression
(α = .15/.30/.50/.70/.90), isotropic scale (.95/.85/.70/.50), sideways shift (5/10/20% of
frame width), rotation (5/15/30°), asymmetric scale (.05/.15/.30). **A corruption is a
model of a wrong calibration, not a sample of one.** Section "The one real wrong
calibration" is where that bill comes due.

## Signals in the mix

Nine were available; **seven are implemented as indicators**, six of them fire.

| indicator | reads | source of its threshold |
|---|---|---|
| `lines` | `verify_court`: coverage / visible_frac / centrality | `verify_court`'s own shipped bars (0.40 / 0.30 / 0.70) |
| `residual` | `cam_fit_quad` px from the nearest physical camera | **TRAIN-chosen, 25 px** (see below) |
| `lens_coherence` | fitted hfov **AND** fitted camera height together | repo's 60–90° amateur-lens prior; 4 m mount ceiling |
| `camera_height` | fitted height below 1 m or above 15 m | physically impossible, not implausible |
| `net_coherence` | `net_tape_clearance` px **AND** fitted height together | +43 px = a 4.00 m mount, off the derivation table in `live-setup-criterion.md` |
| `tape_height` | `net_tape_height.py` tape-implied vs fitted height | the pre-registered 10% bar from that work |
| `player_feet` | deepest player foot in court-y metres | **implemented, never exercised — see NOT ESTABLISHED** |

Two things worth saying about the design, because they are why the mix behaves differently
from its members:

**Coherence, not thresholds.** The lesson of the failed fitted-hfov window was that
`eala_auto` (a real Wimbledon broadcast telephoto, 24.5°) sits *inside* the compression
distribution — no 1-D threshold on hfov can exclude it and still catch compression. But a
narrow lens is only *incoherent* on a **low** mount. Broadcast is narrow-lens + high-mount,
which is a coherent camera; depth compression is narrow-lens + low-mount, which is not a
camera at all. `net_coherence` has the same shape: a tower-sized far-baseline/net-tape
clearance next to a 1.7 m fitted height is a contradiction, not a reading. **This is what
lets the composite catch 91% of depth compressions while scoring `eala_auto` at 0.0.**

**A missing signal is silent, never a vote.** The net tape refuses on `eala_auto` (R4) and
`uR5q2cSM6AY` (R5); no player-feet reading exists for any clip. Absent signals do not
appear in the indicator list at all, and are pinned that way by a test.

## The rule, chosen on TRAIN only

Selection criterion, **declared before the held-out split was touched**: *maximise pooled
TRAIN detection subject to **zero** TRAIN false flags; tie-break toward the simpler rule.*
Search space: `lines` and `tape_height` weights ∈ {0.5, 1.0}, `FLAG_AT` ∈ {1.0, 1.5, 2.0},
residual bound ∈ {25, 40} px. 24 combinations, all evaluated on TRAIN only.

**Winner, frozen into `calib_score.py`:**

```
WEIGHTS = {"lines": 0.5, "tape_height": 0.5}     # every other indicator 1.0
FLAG_AT = 1.0
RESIDUAL_REFUSE_PX = 25.0
```

The two half-weight members are exactly the two that false-flag believed-correct
calibrations on their own — `lines` reads line *contrast* (3 TRAIN clips have paint too
faint) and `tape_height` already scored 13/15 in its own study. Half a vote each means
neither can flag alone but either can confirm another. **This is the whole ensemble idea in
one line**, and it was chosen on TRAIN, not justified after the fact.

**TRAIN performance of the frozen rule: 0 false flags of 17, pooled 187/306 = 61%**
(depth 100%, iso 18%, shift 67%, rot 94%, asym 16%).

`RESIDUAL_REFUSE_PX = 25` is **the one constant here fitted to data** (TRAIN's worst
believed-correct baseline residual was 19.1 px). The repo's own pre-existing bound is 40 px;
that variant is reported as a sensitivity check below and the verdict is **not** taken from
whichever wins. Every other constant is imported from a decision made elsewhere.

## Held-out results, by corruption TYPE

**9 believed-correct clips, 162 corruptions. The rule saw none of these while being chosen.**

| corruption type | flagged | rate | the bar wants ≥80% |
|---|---|---|---|
| **depth compression (anisotropic)** | 41 / 45 | **91%** | **PASS** |
| rotation 5/15/30° | 25 / 27 | **93%** | PASS |
| sideways shift 5/10/20% | 18 / 27 | 67% | fail |
| asymmetric scale .05/.15/.30 | 8 / 27 | 30% | fail |
| **isotropic scale .95/.85/.70/.50** | **0 / 36** | **0%** | **fail — total** |
| **pooled** | **92 / 162** | **57%** | **FAIL (bar 80%)** |

**False flags among believed-correct: 1 of 9 — `flexi_franz_p07`. Bar met (≤1).**

| held-out clip | score | flag | what fired |
|---|---|---|---|
| am_hard_utr | 0.0 | | — |
| demo30 | 0.5 | | tape_height (+80%) — half a vote, correctly not enough |
| **eala_auto** | **0.0** | | **— (the negative that broke two previous screens)** |
| flexi_franz_p01 | 0.0 | | — |
| **flexi_franz_p07** | **1.0** | **FLAG** | lens_coherence (59.5° at 2.3 m) |
| flexi_joy_p07 | 0.0 | | — |
| hillsborough_p08 | 0.0 | | — |
| mpc_tuesday_p01 | 0.0 | | — |
| uR5q2cSM6AY | 0.0 | | — |

**The single false flag is fragile and I will not pretend otherwise.** `flexi_franz_p07`
fits 59.5°, which is **0.5° below** the 60° amateur-lens floor; its sibling clip
`flexi_franz_p01` — same camera, same mount, re-clicked — fits 60.5° and does not flag. I
measured re-click hfov scatter of **up to 29.2°** on the same mount
(`docs/evidence/fitted-hfov-reporting-gap.md`). So this false flag is a coin toss, and the
"≤1 false flag" half of the bar is **met by luck, not by margin**.

### Why isotropic scale is 0/36, and why that is not fixable here

`lines` (coverage) is the only member that responds to isotropic scale, and qa reported it
catches that family. **It catches it relative to the clip's own baseline. It cannot catch it
as an absolute threshold, and at setup time there is no baseline.** On TRAIN, isotropic-0.70
coverage runs median 0.399 / min 0.056 — which **overlaps** three believed-correct baselines
(`HoHxFSX_gLk_s3` 0.188, `CYqapSq5llo` 0.326, `sAjkpeRq4P4` 0.433). Any coverage bar that
catches a scaled court rejects real clips with faint paint. `lines` at half weight then
means isotropic scale needs a *second* signal to confirm it, and none of the others move:
under pure scale the camera fit simply moves the camera, which is the textbook scale
ambiguity and is geometrically correct behaviour.

**Honest restatement:** the composite is blind to isotropic scale for the same structural
reason `verify_court` is — it is the one corruption that produces a *legal* camera view of a
*differently-sized* court, and nothing in the frame says how big a tennis court is except
the paint.

### Sensitivity: the repo's own 40 px residual bound instead of 25

Held-out: **1 false flag (same clip), pooled 79/162 = 49%** (depth 91%, rot 81%, shift 52%,
asym 7%, iso 0%). Same verdict, lower detection. The TRAIN-fitted constant is not what
carries the result.

## Solo-vs-composite ablation

**HELD-OUT.** "FF" = false flags among the 9 believed-correct baselines.

| indicator alone | FF | depth | iso | shift | rot | asym | pooled |
|---|---|---|---|---|---|---|---|
| `lines` | 0/9 | 22% | **28%** | 15% | 19% | 4% | 19% |
| `residual` | 0/9 | 22% | 0% | **63%** | **93%** | **30%** | 37% |
| `lens_coherence` | **1/9** | **76%** | 0% | 7% | 4% | 0% | 23% |
| `camera_height` | 0/9 | 2% | 0% | 4% | 33% | 0% | 7% |
| `net_coherence` | 0/9 | 38% | 0% | 0% | 0% | 0% | 10% |
| `tape_height` | **1/9** | 27% | **28%** | 7% | 0% | 7% | 16% |
| `player_feet` | 0/9 | 0% | 0% | 0% | 0% | 0% | 0% (never fires) |
| **COMPOSITE** | **1/9** | **91%** | 0% | **67%** | **93%** | **30%** | **57%** |

**No single signal alone matches the composite. The ensemble is not redundant.** The bar
asked me to say plainly if one member carried it; the measurement says the opposite, and
that is the substantive positive result of this run:

- On **depth compression**, the composite (91%) beats the best member (`lens_coherence`,
  76%) by 15 points **and** the best member is the one that produces the false flag. The
  composite gets the extra 15 points from `net_coherence` (38%) and `tape_height` (27%)
  covering the severe compressions where the fit has already collapsed.
- On **pooled**, the composite (57%) beats the best member (`residual`, 37%) by 20 points.
- The members really are decorrelated as the pre-registration argued: `residual` owns
  rotation and shift, `lens_coherence` owns depth, `lines` and `tape_height` are the only
  two with any isotropic response at all, and none of them overlaps another's specialty.

The one place the mix *costs* something: `lines` solo catches isotropic 28%, and the
composite catches 0%, because half a vote cannot flag alone. That is the price paid for
holding false flags to 1, and it is the reason the pooled bar fails.

## The one real wrong calibration (n=1)

`data/yt_match40_pts.json.bak-2026-09-05` — corners clicked on asphalt and a hedge, the
calibration that stamped **PASS at 0.9 px residual** and produced trap T23.

**The composite scores it 0.0. Nothing fires. Not one indicator.**

| | fitted height | fitted hfov | coverage | residual | net clearance | tape |
|---|---|---|---|---|---|---|
| `.bak` (**WRONG**) | 10.82 m | 20.9° | 0.436 | 12.4 px | +9.0 px | refused (R3) |
| `eala_auto` (**CORRECT**, broadcast) | 8.73 m | 24.5° | 0.921 | 4.5 px | +7.2 px | refused (R4) |

**The wrong calibration and the correct broadcast camera are the same camera to five of the
six signals.** 2 m of height and 4° of lens apart. The coherence rule that saves `eala_auto`
— narrow lens is fine on a high mount — is exactly what exonerates the `.bak`. Its coverage
(0.436) is *above* `verify_court`'s 0.40 bar and *below* four believed-correct clips
(`HoHxFSX_gLk_s3` 0.188, `CYqapSq5llo` 0.326, `sAjkpeRq4P4` 0.433, `UHf0LeMU2pg` 0.512), so
the one signal that does separate them cannot be given a threshold that does.

**I did not retune to catch it, and the miss is pinned by a test**
(`test_the_one_real_wrong_calibration_is_MISSED_and_this_is_pinned`) so nobody quietly fixes
it later. n = 1; every constant that would catch it re-breaks `eala_auto`; and fitting a
rule to a single positive is how this project got T23 in the first place.

**What this actually means for the product.** The synthetic positives are all *low-mount
amateur* corruptions, and on those the composite does well. The one real failure was a
*high-mount-looking* mis-click. **The synthetic class does not cover the failure mode that
actually happened.** Any future confidence in this scorer needs more real wrong
calibrations — deliberately mis-clicked by a human and labelled as such — not more
corruption families.

## Reason strings it emits

Every flag carries a sentence a human can act on. Real output, unedited:

- **depth compression, mild** (`A7vXlWIlyrI`, α=0.15) —
  *"This court may be wrong: fitted lens is implausibly narrow (49 deg) for a 1.7 m mount —
  the far half of the court looks compressed toward the net."*
- **depth compression, severe** (`am_hard_utr`, α=0.50) —
  *"...fitted lens is implausibly narrow (16 deg) for a 2.1 m mount — the far half of the
  court looks compressed toward the net; the far baseline sits 591 px above the net tape,
  which needs a mount well above 4 m, but the corners fit a 2.1 m camera."*
- **sideways shift** (`A7vXlWIlyrI`, 10% of width) —
  *"...the four corners are 31 px from any physically possible camera view of a tennis
  court."*
- **rotation** (`A7vXlWIlyrI`, 15°) —
  *"...the four corners are 78 px from any physically possible camera view of a tennis
  court; fitted camera height 0.6 m is not a place a camera can be."*
- **several at once** (`CYqapSq5llo`, α=0.70) —
  *"...the court is off to one side of the frame; fitted lens is implausibly narrow (6 deg)
  for a 2.3 m mount...; the far baseline sits 387 px above the net tape, which needs a mount
  well above 4 m, but the corners fit a 2.3 m camera; the net tape puts the camera +339%
  away from the height the court corners give."*
- **clean** — *"Every check agrees on this court."*

The reason string is the deliverable a human uses; the score is only how the reasons are
counted. A rule that could not say *why* would fail this project's own standards even at
100%.

## Where it is wired

`backend/swingvision/calib_score.py` — `composite_score(signals) -> CalibScore` and
`explain(score) -> str`. Deliberately a **pure function over an already-computed signal
dict**: it decodes nothing, loads no model, and has no I/O, so it is trivially portable to
the phone and testable without video. The callers that already compute these signals
(`run.py check`'s setup block, `tools/validate_new_clip.py`, `courtfit.setup_verdict`) can
each hand it what they have; a signal they do not have is silently absent.

**It is not wired into any accept/reject path and must not be** until a founder says so.
`run.py`'s parser was not touched (NOT-THIS-RUN).

## NOT ESTABLISHED THIS RUN

- **The player-feet depth anchor never fired.** The indicator is implemented and tested
  (`feet_max_y_m`), but no clip in the sweep has a feet reading: YOLO-pose weights
  auto-download on first use (no network on this box, and none allowed), and the handful of
  cached `*.perception.json` files do not cover these 27 clips at frame 0. **This is the one
  signal in the mix that reads an object standing ON the court**, i.e. the only one that is
  not a function of the four clicked corners plus the paint, so its solo and marginal
  contribution are genuinely unknown — not zero, unmeasured.
- **`FLAG_AT`, `WEIGHTS` and `RESIDUAL_REFUSE_PX` were chosen on 17 clips.** A second seeded
  split was not run; the stability of the choice is unmeasured.
- **The `flexi_franz_p07` false flag was not eye-checked.** It may be a genuinely marginal
  clip rather than a rule error; only a human looking at the frame can say.
- **`demo30`'s tape reads +80%** against its own fitted height while every other held-out
  clip reads within 8%. Not chased. It is a synthetic clip and its speeds are already
  non-citable, but an 80% off-plane disagreement on a believed-correct calibration is
  unexplained.
- **No isotropic-scale detector exists**, and this run argues none can exist from a single
  frame plus four corners. Not proved, argued.

## What would have to be true for this to become a gate

Not this run's call, but the shape of the answer: more **real** wrong calibrations. The
synthetic class is a model of failure written by us; the one real failure it does not
resemble is the one that actually happened. A dozen human mis-clicks, labelled, would tell
you more than another five corruption families.
