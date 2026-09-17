# Does camera motion degrade court detection? Inter-frame agreement, before and after motion compensation

**qa, 2026-09-09.** Independent verification run. No shipped code, threshold, vote, lock
step, watchdog or `*_pts.json` was touched. Measurement only.

## HEADLINE

**Motion is a real but secondary term. Removing it does not rescue a single clip.**

- On the 5 clips that genuinely move within the scored window, motion compensation removes
  a median **24.0 px@640** of inter-frame disagreement — more than one full wrong-court
  distance. So the pixel-space vote **is** partly rejecting camera motion. That part of the
  founder's hypothesis is confirmed and quantified.
- But it leaves a median **26.4 px@640** still on the table, and the 11 clips that do *not*
  move sit at **24.8 px@640**. **After motion is removed the two groups are the same.**
  The disagreement floor is motion-independent.
- Across the pool, exactly **1 of 16** measurable clips crosses from "fits disagree by more
  than a wrong court" to below it (`HoHxFSX_gLk_s2`, 41.6 → 15.7 px@640).
- **Acceptance changes on 0 of 20 clips.** Votes move on two (`CYqapSq5llo` 2→4,
  `HoHxFSX_gLk_s2` 2→3); neither reaches `ACCEPT_VOTES = 6`.

**Verdict against the pre-registered bar: BAR 1 INDETERMINATE, BAR 2 PARTIAL, BAR 3 LINKED
but underpowered (n=3).** Nothing was re-banded after the fact.

## THE PRE-REGISTERED BAR

Written into `.claude/journals/qa.md` before the first court fit was run (repo rule 2).
Reproduced verbatim in substance:

- `D_raw(c)` = median over all pairs of locked frames of the mean 4-corner distance between
  their two quads, in **raw pixels** — exactly what `courtfit.consensus` compares — reported
  in px@640.
- `D_comp(c)` = the same after each frame's quad is mapped into the first scored frame's
  pixel space by an ORB+RANSAC background similarity transform. Cut frames excluded and named.
- `M(c)` = measured background displacement. `WRONG_PX_640 = 20.0` anchors every band.

| bar | condition | result |
| --- | --- | --- |
| **1 — does motion drive raw disagreement?** | DRIVES if rho(M, D_raw) >= +0.60 **and** median D_raw gap (M>=20 vs M<20) >= 20.0 px. DOES NOT if rho <= +0.20 **or** gap < 10.0 px. Else INDETERMINATE. | **rho = 0.474, gap = 18.6 px → INDETERMINATE.** Both halves land inside the dead band. Not rounded either way. |
| **2 — apparent or real?** | APPARENT if median (D_raw − D_comp) >= 20.0 **and** median D_comp < 20.0. REAL if median D_comp >= 20.0. PARTIAL if the drop >= 20.0 but D_comp still >= 20.0. | **drop = 24.0, D_comp = 26.4 → PARTIAL.** |
| **3 — is width disagreement a zoom effect?** | LINKED if median width spread among clips with >=5% scale change is >= 2x that among clips with <2%. | **16.4% vs 7.1%, ratio 2.30 → LINKED**, on **n = 3 zoom clips**. |

**Power, stated in advance and confirmed by the result:** n = 20 clips, 16 measurable, and
only **5** carry M_win >= 20 px. A Spearman rho on this n is weak evidence and almost all
its leverage sits in those 5 clips; one clip moves it. Group sizes are printed beside every
correlation below. I do not present rho alone as a finding.

## INSTRUMENT AND ITS CONTROLS

Per clip: decode the 8 frames `run_refs.frame_positions(total, 8)` scores, run
`courtfit.auto_fit_frame` on each (the exact per-frame fit the vote consumes), estimate
background transforms between them (ORB 6000 features, ratio test, `estimateAffinePartial2D`
RANSAC at 960 px working width), and **re-invoke `courtfit.consensus` itself** on the
compensated quads rather than re-deriving the vote (per T-series: predict a behaviour by
invoking it).

Four independent validations, three of them against numbers this run did not produce:

1. **NULL control, every clip**: frame vs itself → **0.000 px@640 on all 20.**
2. **POSITIVE control, every clip**: an injected 8.000 px@640 translation recovered as
   **7.98–8.04 px on all 20.** The instrument responds at the decision scale.
3. **Lock counts match the shipped audit exactly** on all 9 clips the brief quoted from
   `data/output/ai_court_audit/index.json`: `mpc_mixed_p02` 0/8, `mpc_mixed_p08` 0/8,
   `mpc_tuesday_p07` 0/8, `mpc_tuesday_p01` 1/8, `flexi_joy_p01` 2/8, `sAjkpeRq4P4` 8/8,
   `HoHxFSX_gLk_s2` 8/8, `CYqapSq5llo` 8/8, `uR5q2cSM6AY` 8/8.
4. **Acceptance reproduces STATE row 196**: this harness accepts **2 of 20** references,
   which is precisely that row's classical-arm figure ("References: **2/20**").
   `courtfit.resolved_proposer(None)` was confirmed to be `"classical"` — the shipped arm.

**Instrument limitation, stated not hidden.** A 2-D similarity is exact for a camera that
pans/rolls/zooms about its optical centre; it is only an approximation if the camera
translates in space. On a translating camera `D_comp` is an **over**-estimate of the
residual, so the compensation result is conservative in the direction of my verdict — it
cannot manufacture the "the disagreement is real" conclusion, only understate it. Frames
with no shared background (RANSAC inliers < 30, or absurd scale/rotation) are **cuts**, not
displacements: excluded from `D_comp` and counted in the `cut` column.

## THE MOTION COVARIATE HAD TO BE RE-MEASURED — the prior number is the wrong quantity

Yesterday's `docs/evidence/camera-motion-verdict-risk.md` measured displacement **against
video frame 0**, because the question there was frame-choice risk in a rendered audit sheet.
The vote compares the 8 *scored* frames with **each other**, so the covariate this question
needs is motion **within the eval window**. They differ sharply:

| clip | vs video frame 0 (`M_f0`) | within eval window (`M_win`) |
| --- | ---: | ---: |
| `sAjkpeRq4P4` | 80.4 | **3.6** |
| `HoHxFSX_gLk_s1` | 535.4 | 101.9 |
| `A7vXlWIlyrI` | 162.6 | 108.7 |

`sAjkpeRq4P4` is the clean example: frame 0 is a zoomed-in title shot far from everything
the eval sees, but the eight scored frames are mutually static. Yesterday's number is
correct for yesterday's question and wrong for this one. `M_win` is used as primary here and
this substitution is disclosed rather than folded in: **the bar as written named `M = Dc`.**
Both are reported, and using the pre-registered `M_f0` instead makes the correlation
*weaker* (rho 0.379 vs 0.474), so the substitution does not flatter the result.

## FULL TABLE — 20 clips, sorted by within-window motion

`lk` = frames locked of 8. `M_win`/`M_f0` px@640. `D_raw`/`D_comp` = median pairwise
inter-frame court disagreement, px@640. `dD` = the drop. `W_near` = median pairwise
fractional disagreement in the fitted **near** doubles-baseline length; `W_far` the far one.
`v_raw`/`v_cmp` = `courtfit.consensus` votes before/after compensation (`ACCEPT_VOTES = 6`).

| clip | res | lk | M_win | M_f0 | D_raw | D_comp | dD | W_near raw | W_near comp | W_far raw | v_raw | v_cmp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A7vXlWIlyrI | 1920 | 4 | 108.7 | 162.6 | 44.2 | 20.1 | **24.0** | 11.1% | 6.4% | 38.2% | 1 | 1 |
| HoHxFSX_gLk_s1 | 1920 | 3 | 101.9 | 535.4 | 116.5 | 69.5 | **47.0** | 56.5% | 33.5% | 17.8% | 1 | 1 |
| HoHxFSX_gLk_s2 | 1920 | 8 | 81.2 | 110.5 | 41.6 | **15.7** | **25.9** | 16.4% | 6.5% | 20.1% | 2 | 3 |
| CYqapSq5llo | 1920 | 8 | 31.3 | 38.8 | 32.5 | 26.4 | 6.1 | 6.5% | 7.5% | 15.7% | 2 | 4 |
| UHf0LeMU2pg | 1920 | 7 | 20.5 | 29.2 | 51.3 | 44.3 | 6.9 | 17.0% | 17.9% | 14.6% | 2 | 2 |
| uR5q2cSM6AY | 1920 | 8 | 15.8 | 13.2 | 27.1 | 26.6 | 0.5 | 15.3% | 15.5% | 10.4% | 3 | 3 |
| e8T34KoJzOw_s2 | 1920 | 8 | 6.0 | 9.7 | 25.6 | 24.8 | 0.8 | 7.9% | 7.6% | 13.9% | 2 | 2 |
| am_hard_utr | 1920 | 8 | 5.1 | 11.9 | **6.7** | 5.4 | 1.3 | 2.4% | 2.2% | 2.4% | **7** | 7 |
| sAjkpeRq4P4 | 1920 | 8 | 3.6 | 80.4 | **4.5** | 3.6 | 1.0 | 1.5% | 1.6% | 3.5% | **6** | 6 |
| flexi_joy_p01 | 3840 | 2 | 0.3 | 0.3 | 29.9 | 29.9 | 0.0 | 5.7% | 5.7% | 22.4% | 1 | 1 |
| mpc_tuesday_p01 | 3840 | 1 | 0.3 | 0.3 | — | — | — | — | — | — | 1 | 1 |
| tc8CGFxyRE8 | 1920 | 7 | 0.2 | 0.4 | 24.2 | 24.2 | −0.0 | 6.3% | 6.4% | 7.4% | 3 | 3 |
| mpc_tuesday_p07 | 3840 | 0 | 0.1 | 0.1 | — | — | — | — | — | — | 0 | — |
| flexi_franz_p07 | 3840 | 3 | 0.1 | 0.2 | 20.8 | 20.8 | −0.0 | 8.4% | 8.4% | 4.3% | 1 | 1 |
| flexi_joy_p07 | 3840 | 5 | 0.1 | 0.1 | 37.5 | 37.5 | 0.0 | 9.8% | 9.8% | 34.9% | 1 | 1 |
| hillsborough_p02 | 3840 | 3 | 0.1 | 0.1 | 31.9 | 31.9 | −0.0 | 3.3% | 3.4% | 93.9% | 1 | 1 |
| mpc_mixed_p02 | 3840 | 0 | 0.1 | 0.1 | — | — | — | — | — | — | 0 | — |
| flexi_franz_p01 | 3840 | 3 | 0.0 | 0.0 | 9.1 | 9.1 | 0.0 | 3.4% | 3.4% | 9.2% | 1 | 1 |
| hillsborough_p08 | 3840 | 3 | 0.0 | 0.1 | 36.3 | 36.2 | 0.0 | 14.5% | 14.5% | 23.0% | 1 | 1 |
| mpc_mixed_p08 | 3840 | 0 | 0.0 | 0.0 | — | — | — | — | — | — | 0 | — |

**UNMEASURABLE, named not counted (my bar requires >= 2 locked frames):**
`mpc_mixed_p02`, `mpc_mixed_p08`, `mpc_tuesday_p07` (0 locks each) and `mpc_tuesday_p01`
(1 lock). All four are shell. They are absent from every statistic below and are **not**
counted as agreeing. `HoHxFSX_gLk_s1` (3 cut frames) and `_s2` (2) have `D_comp` computed
from their non-cut frames only.

## BAR 1 — MOTION AND RAW DISAGREEMENT: INDETERMINATE

| | value | bar |
| --- | ---: | --- |
| Spearman rho(`M_win`, `D_raw`), n = 16 | **+0.474** | >= +0.60 drives / <= +0.20 does not |
| Spearman rho(`M_f0`, `D_raw`), n = 16 | +0.379 | (pre-registered covariate) |
| median `D_raw`, `M_win` >= 20 (**n = 5**) | 44.2 | |
| median `D_raw`, `M_win` < 20 (**n = 11**) | 25.6 | |
| gap | **18.6 px@640** | >= 20.0 drives / < 10.0 does not |

Both halves land in the dead band, and the group half misses by 1.4 px. **INDETERMINATE.**
I am not rounding an 18.6 up to a 20 or a 0.474 up to a 0.60. The honest reading is that
motion *contributes* to raw disagreement and does not *dominate* it — which is what Bar 2
then resolves directly.

**The confound I flagged in advance still stands and is not separable on this pool.** Source
type predicts both motion and surface: the 11 low-motion clips include all 10 shell
recordings (locked-off 4K tripods) plus `tc8CGFxyRE8`, while the 5 high-motion clips are all
1920-wide edited YouTube material. Any "motion effect" here is inseparable from a
surface/resolution effect. Nothing in this measurement separates them.

## BAR 2 — IS THE DISAGREEMENT REAL OR APPARENT? PARTIAL, and the control is decisive

| group | n | median `D_raw` | median `D_comp` | median drop |
| --- | ---: | ---: | ---: | ---: |
| high motion (`M_win` >= 20) | 5 | 44.2 | **26.4** | **24.0** |
| low motion (`M_win` < 20) | 11 | 25.6 | **24.8** | **0.01** |

Three things follow, in order of how much weight they carry:

1. **The founder's mechanism is real and worth 24 px.** On the moving clips, compensating
   for the camera removes more than a full wrong-court distance of apparent disagreement.
   Those frames were being penalised for the camera, not only for their detections.
2. **It is not enough to matter.** `D_comp` on those clips is still 26.4 px@640, above the
   20 px wrong-court line. By my own pre-registered definition that is **PARTIAL**, not
   APPARENT.
3. **The control settles it.** On the 11 static clips compensation is a **0.01 px** no-op —
   exactly as it must be, which is itself a check that the transform is not injecting
   anything — and those clips *still* disagree by **24.8 px@640**, statistically
   indistinguishable from the moving clips' post-compensation 26.4. **Four completely static
   4K shell clips disagree with themselves by 29.9, 31.9, 36.3 and 37.5 px@640 with zero
   camera motion of any kind.** Whatever is driving inter-frame disagreement on this pool is
   overwhelmingly not the camera.

Pool-level: `D_raw` >= 20 px on **13 of 16** measurable clips; `D_comp` >= 20 px on **12 of
16**. Pool median 26.4 → 25.6 px@640. **Exactly one clip crosses the line**
(`HoHxFSX_gLk_s2`). **Zero clips change acceptance**; `CYqapSq5llo` gains 2 votes and
`HoHxFSX_gLk_s2` gains 1, and both remain far from `ACCEPT_VOTES = 6`.

## BAR 3 — THE WIDTH DIMENSION: linked to zoom on 3 clips, not an explanation of STATE's row

STATE carries an open row: *frames that find the RIGHT court disagree about its WIDTH*,
13 of 18 clips. Measuring the fitted near-baseline length spread across the scored frames:

| group | n | median `W_near` raw | median `W_near` compensated |
| --- | ---: | ---: | ---: |
| zoom (`\|log scale\|` >= 5%) | **3** | **16.4%** | **6.5%** |
| static (`\|log scale\|` < 2%) | 12 | 7.1% | 7.1% |

Ratio **2.30** against a pre-registered 2.0 → **LINKED**, and the mechanism is confirmed
rather than inferred: removing the scale change drops the zoom group from 16.4% to 6.5%,
landing it on the static group's 7.1%. Zoom fully accounts for the *excess*.

**But it does not account for the row.** The zoom group is **3 clips** —
`A7vXlWIlyrI`, `HoHxFSX_gLk_s1`, `HoHxFSX_gLk_s2`, i.e. the same three extreme-motion clips
that carry every other effect in this study — and a 2.30 ratio on n=3 vs n=12 is a
one-clip-fragile result. Meanwhile **12 of 16** measurable clips disagree about near-baseline
width by >= 5%, and **8 of those 12 are among the fully static clips**, where zoom is
identically zero. The far baseline is worse and equally motion-free: `hillsborough_p02`
**93.9%**, `flexi_joy_p07` **34.9%**, `flexi_joy_p01` 22.4%, `hillsborough_p08` 23.0% — all
on tripods measured at under 0.3 px of motion.

**Reported verdict: the zoom link passes its bar but is underpowered and cannot carry STATE's
row.** The width disagreement is predominantly a static-clip phenomenon.

## WHAT ACTUALLY PENALISES CLIPS IN THE PIXEL-SPACE VOTE — and it is not motion

`courtfit.AGREE_PX = 30.0` (courtfit.py:774) is compared in the clip's **raw** pixels by
`_corner_dist` (:778, used at :789) and is **not** resolution-scaled, contrary to CLAUDE.md's
"every pixel threshold scales by `frame_height/720`". In the project's own unit that is
**30 px@640 at 640 wide, 10.0 at 1920, 5.0 at 3840** — the agreement window is 6x tighter on
the 4K shell clips than on the gold pool, against an accepted-court band of 3.4–13.9 px.

**This is already established and is not my finding**: see
[`agree-px-is-6-tighter-on-4k.md`](agree-px-is-6-tighter-on-4k.md), which additionally
measured that normalising it is an exact no-op on gold (12/20 → 12/20), takes shell 0 → 2
accepted, and **admits two wrong courts on the 1920 references** (`tc8CGFxyRE8` 58.7 px,
`e8T34KoJzOw_s2` 28.7 px). I cite it here only because it is the direct answer to the
brief's second question: **the pixel-space agreement test does penalise a group of clips
specifically, and that group is defined by RESOLUTION, not by motion.** My independent
numbers are consistent with it — the four static 4K clips with `D_raw` of 29.9–37.5 px@640
are being asked to agree within 5.0.

## WHAT THIS ESTABLISHES, AND WHAT IT DOES NOT

**Establishes:**
- The runtime half of the founder's hypothesis is not at issue here and was already refuted
  by the lead from source (`pipeline.py:1092` re-snaps every processed frame; `CourtWatchdog`
  re-bases every 30). This measurement is about the *instruments*, which do read one frame.
- The instruments' pixel-space vote **is** partly penalising camera motion, worth a median
  24.0 px@640 on the 5 clips that move — real, quantified, previously unmeasured.
- That penalty changes **no clip's acceptance** and moves **one clip** across the wrong-court
  line. Inter-frame disagreement on this pool is overwhelmingly not camera motion.
- Width disagreement is a zoom effect on the 3 zooming clips and is **not** a zoom effect on
  the 12 static ones.

**Does not establish, explicitly:**
- **Nothing here says camera motion explains the 40% proposal recall.** It cannot: the three
  clips producing no lock at all (`mpc_mixed_p02`, `mpc_mixed_p08`, `mpc_tuesday_p07`) are
  locked-off tripods measured at 0.02–0.08 px@640. That door stays closed.
- **Lock rate is not correctness, and this study is a case in point.** `sAjkpeRq4P4` locks
  8/8, disagrees with itself by only 4.5 px@640 and passes the vote at 6 — and it is one of
  the 10 clips the founder marked as a **wrong** court placement. High inter-frame agreement
  is consistent with a consistently wrong court. `D_raw` measures self-consistency and says
  nothing whatever about accuracy.
- **No number here is accuracy.** Nothing in this file is scored against the human-clicked
  corners; every figure is fit-vs-fit. Where the human pool is touched at all (the vote
  counts, for reproducing STATE row 196), the standing caveat applies: those calibrations
  are **under review** — 10 of 28 sheets marked wrong, 7 of the 10 flagged verdicts
  unresolved (TRAPS T26, [`calibration-provenance.md`](calibration-provenance.md)).
- 4 of 20 clips are **unmeasurable** on this question because they never produce two locks.
  Their disagreement is undefined, not zero.
- n = 16 measurable, 5 of them moving. Every correlation above is weak evidence, and the
  motion/surface/resolution confound is not separable on this pool.

## BORDERLINE, FOR A HUMAN TO LOOK AT

- **Bar 1's group half missed by 1.4 px** (18.6 vs 20.0) while its rho half missed clearly
  (0.474 vs 0.60). If anyone wants to argue motion "drives" disagreement, that 18.6 is the
  number they will reach for. It fails the bar as written and the bar does not move.
- **Bar 3 passes at n = 3.** A 2.30 ratio resting on three clips, all of which are also the
  three highest-motion clips in the pool, is the weakest number in this file.
- **`hillsborough_p02`'s 93.9% far-baseline width spread** across 3 locked frames on a
  motionless 4K tripod is extreme enough to be worth an eye on the rendered frames before
  anyone builds on it.

## RAW DATA

`scratchpad/interframe_agreement.py` → `interframe.json` (per clip: positions, per-frame
lock, cut flags, scales, all pairwise distances, controls),
`scratchpad/window_motion.py` → `window_motion.json` (within-eval-window displacement), and
`scratchpad/motion.json` from the prior run (displacement vs video frame 0). Held outside
the repo because measurement scaffolding is not product code; regenerate from the scripts.
