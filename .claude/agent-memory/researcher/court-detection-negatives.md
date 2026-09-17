---
name: court-detection-negatives
description: Every court-detection approach already measured and rejected here, with the reason — check before proposing anything about the court search
metadata:
  type: project
---

Backfilled 2026-08-27 from `docs/STATE.md`, `docs/RESEARCH_BRIEF_indoor_shell_courts.md`,
`docs/archive/sessions/SESSION_O_shell_courts.md`, `docs/archive/resolved/`.
Also read `docs/STATE.md` "What has not worked" (~50 rows) before proposing anything.

| Approach | Outcome |
|---|---|
| **Widen the seed grid** (all 30 human-labelled courts fall outside the shipped far-width range — the grid searches 0.20-0.42 of frame width, real courts sit at 0.09-0.22) | **REJECTED.** Reaches courts the old grid could not and **gets every one of them wrong** — 26 px and 78 px. Would have been the first wrong court ever accepted. Corrected the earlier five/five split: the half called a search failure was really scoring, and reachability was hiding it. |
| **Global mask replacement — CLAHE local contrast, Lab a\*/b\* chroma fusion, both** | **REJECTED on the product gate.** Fixes clay, breaks hard courts: chroma_only 9/20, clahe_only 13/20 with two courts at 22.4 px, both 6/20. Key finding: **chroma and CLAHE are redundant substitutes** — either alone gives the whole gain, both gives no more. Reading single ablations alone said "neither matters", an artefact of removing one while the other covered. |
| **Surface-routed clay mask** | **SHIPPED 2026-08-20 — the only court change to clear the gate.** 11/20 -> 12/20, nothing lost, zero wrong courts, median error 8.3 -> 8.1 px. Judge the surface, then use the mask built for it. Non-clay frames take a **bit-identical** path (pinned by `test_court_surface_routing.py`). Surface separates on colour alone: clay a\* 148.0-163.5 vs 132.0 max for everything else, `CLAY_A_STAR = 140.0`. CLAHE ships over chroma because chroma loses `sAjkpeRq4P4`. |
| **Broadcast-pose seeding** (27 synthetic 6-18 m long-lens poses) | **REJECTED.** No change on any clip. |
| **Crop-and-upscale** ("the court is too small in the frame", x1.18 -> x2.50) | **REJECTED.** No change; one clip got *worse* as its corners cropped out. |
| **Camera-angle selection** (human-picked top-down-only frames on broadcast) | **REJECTED.** No change, 0 of 6. |
| Surface routing to the *existing* hue-agnostic clay mask | Bit-identical to baseline — the pipeline already falls back to it. A better clay mask was needed, not an earlier reach for the old one. |
| Building the court quad from the DETECTED LINES | **Wrong in principle, not mis-tuned.** Under perspective the two doubles sidelines converge, so they form no angular cluster. Best constructed quad 68-256 px from truth vs the lattice's 7-20. |
| Snapping a near-correct court onto detected lines | Median distance from truth: seed 9.8 -> refiner 8.4 -> **snap 70.5**. Needs joint line-to-model assignment. |
| Raising `topk` (12 -> 40 -> 150) | No clip moves, **7x compute** (32 s -> 229 s per 4 frames). |
| Removing the pose-prior weight from seed ranking | No clip improves; the prior is not what buries the true seed. |
| Reachability ("refinement cannot travel from seed to true court") | **STOPPING RULE FIRED.** On **31 of 38** clips the nearest seed is already within reach. The brief predicted the opposite in advance. |
| Narrowing `EVID_BAND` | **The band is INERT** — `n_included` = 10 of 10 on every clip at every band from 5.0 down to 1.0. The hypothesis the whole brief was built around is refuted. Narrowing is a *wrong-court* lever: it raises wrong courts' scores while leaving truth unmoved. |
| Observability from geometry instead of nearby paint | **+0.000 margin**, byte-identical. The free half buys nothing, so the expensive half is unjustified. Closed. |
| Behind-camera projection inflating the denominator | **0.0%** of samples affected. |
| Low true-court score being human click error | Swept `tol` x0.5 -> x4; no clip shows the steep-then-plateau signature click error would produce. |
| Player-foot gate as a wrong-court criterion | **DEAD, and its sign is backwards** — feet-in-court fraction is *higher* for WRONG courts at every margin. The statistic rewards a court for being large. Best catch 2.0% at the <=5% collateral ceiling. |
| The horizon crop (`movers.crop_row`) at `k = 1.0` | **Safe but inert** — a crop is proposed on 1 of 20 clips. `k` was NOT re-tuned, per the brief's own rule. |
| Lowering the consensus bar 6/8 -> 5/8 | Gate fails — the one 5-vote clip is wrong by 68.7 px. |
| Single-frame court auto-seed in the setup tool | **7 of 10 worse** than starting from a blank rectangle. |
| Improving CourtNet for auto-calibration | Wrong target. CourtNet is Tier 2 (20.2% held-out); `courtfit` consensus is Tier 1 and beats it. |
| Vanishing-point filtering as a court/not-court classifier | **Closed by argument.** A shared VP proves 3D parallelism, not coplanarity; floor and roof relate by a planar homology whose axis is the horizon. A building aligned with the court is indistinguishable by line direction alone. |

**Where court detection actually stands:** the detector **finds** the court's lines (the
four outer lines sit a median 1.3-4.1 px@640 from a detected line) but **cannot assemble
them**. The criteria *do* recognise the correct court (9 of 10). The search *does*
produce it (7 of 10). **The frames that each found it do not agree with each other** —
and 13 of 18 clips disagree principally about how **WIDE** the court is, not where it is.
The one build named and never tested is **joint line-to-model correspondence** (assignment
solved together with the homography, Farin-style); its gate was pre-registered 2026-08-27.

**UPDATE 2026-09-05 — joint correspondence was built, measured, and killed; the bottleneck
is now named as the LINE DETECTOR, and court auto-detection is CLOSED as a research
question for v1.** Built 2026-08-29 (three failures: C6 cost 12.6x, 22/30 die before
scoring, C3 reconstructs at 17.1 px@640 even given the TRUE correspondence — worse than
shipped 8.1 px). Two continuations then killed it for good, 2026-09-04:
`verify-court-false-rejects.md` shows the shipped accept gate's coverage/centrality
statistic **orders clips by line VISIBILITY, not correctness** — `yt_match40` (T23,
grossly wrong) PASSES at 0.436, above two correct courts — so no threshold retune fixes
it. `least-squares-court-fit.md` handed the solver the PERFECT correspondence and
optimised over every matched line (not just 4): it drives the line residual to **3.01 px,
below the human homography's own 6.44 px, on 13 of 13 clips** — the optimiser is not the
problem — yet reconstruction is *worse* (19.80 vs 17.10 px). **The ~6.4 px line-truth
disagreement is the ceiling, one stage upstream of the fit and the search both**, and no
fit strategy (4-point, all-lines-LS, DLT) beats it because the line evidence itself does
not contain a better answer. My 2026-09-05 assessment
([[court-detection-path-after-the-line-ceiling]] — see
`docs/evidence/court-detection-path-after-the-line-ceiling.md`) finds the 6.4 px gap is
the SAME ORDER as the human corner-click neighbourhood itself (~5.8 px, from
`eval/truth_neighbourhood.py` / the withdrawn `0.18-0.31` STATE row) — so a large share of
it may not be a fixable detector defect at all, just label/definitional noise (paint
width + blur) that no line-based method, classical or learned, can beat. **Recommendation:
manual calibration is the product answer for v1, not a fallback** — it already ships
(`run.py check`, Court Setup tool), already works, and is what every accuracy number in
this project is measured against. CourtNet-keypoints and dense-segmentation alternatives
were both considered and rejected on the same evidence (CourtNet already closed per row
above — Tier 2 loses to Tier 1 even capped; segmentation would attack coverage, not the
precision ceiling that is actually binding). **The one cheap test that could reopen this**
(not yet run): click points directly ALONG each court line (not just the 4 corners) on a
handful of gold frames, and measure the detector's residual against THAT — if it comes
back >10 px, the detector has real fixable bias and a narrow re-open is justified; if
~5-7 px, the ceiling is corroborated as near-irreducible.

**UPDATE 2026-09-09 — two things that reframe the record. Both are ASSESSMENTS, not
measurements** (`docs/evidence/court-recall-what-would-actually-move-it.md`).

1. **"The search binds" is being MISREAD.** The 2026-09-09 proposal-recall row and the
   older rows in this table (widen seed grid REACHES truth and gets it wrong; `topk`
   12->150 moves no clip; reachability stopping rule) only reconcile one way: **the seed
   ENUMERATION is adequate and the OBJECTIVE's argmax is not the true court.** Say
   "the proposal STAGE binds", never "the search binds" — three readers have taken it as
   "enumerate more", which is a re-proposal of two dead rows.
2. **~30 px@640 static self-spread is a MIXTURE, not a precision floor** (confidence 0.72).
   Hough quantisation accounts for only ~1-4 px@640 (1 deg theta bin levered over a 1500 px
   sideline at 3840 = 4.4 px@640 worst case, less after length-weighted merging), so the
   floor reading is off by 7-30x. The error is ANISOTROPIC — near-baseline width spread
   3.3% vs far-baseline **93.9%** on the same motionless tripod — which noise is not.
   Mechanism: `_ori_detail` correctly excludes lines with no nearby paint as UNMEASURABLE,
   and on a low mount the net tape covers the far baseline, so the only observable pinning
   court DEPTH disappears and the fit slides along a depth/width family at near-constant
   score. `autodetect` is a discrete argmax over <=topk=12 refined seeds, so its 8 frames
   sample a mixture over hypotheses. **Cheapest falsifier, data already exists**
   (`scratchpad/interframe_agreement.json`): cluster the per-frame quads; tight clusters
   far apart = mixture, one loose cluster = floor.

**AND THE LIVE LEAD, unproposed anywhere: `AGREE_PX` cannot be the shell cause.** It is
read only by `consensus`; a clip locking **0 of 8 frames** was refused by the PER-FRAME
path. That path has five constants violating CLAUDE.md's `frame_height/720` rule:
`Sobel(ksize=3)` orientation map (courtfit.py:127 — a 3x3 operator on ~12 px-wide paint at
4K returns noise, and `_ori_detail` demands `align>=0.80`), `HoughLinesP(threshold=45)`
(:73, ~6x easier at 4K), `maxLineGap=12`/`14` (:74,:111, ~6x stricter at 4K),
`cv2.line(...,thickness=2)` in `_clay_mask` (:115 — the SHELL path re-rasterises its own
evidence as 2-px hairlines), `snap_court(max_move_px=30.0)` (:918). Accept rate falls
monotonically with capture resolution: 640 gold 12/20 -> 1920 refs 2/20 -> 3840 shell 0/8.
**Not in "What has not worked" (checked lines 138-206). Not proposed — court is closed for
v1.** Falsify it cheaply by checking whether `calibration.court_line_mask` skeletonises to
1 px; if it does, the Sobel argument weakens sharply.

Related: [[sensor-court-priors]], [[open-questions]], [[project-method-rules]],
[[amateur-court-literature]]
