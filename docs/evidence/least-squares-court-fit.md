# Least-squares over ALL matched line correspondences — the 17.1 px ceiling does not move

> Evidence for the **joint line-to-model correspondence** row in
> [docs/STATE.md](../STATE.md). Executes the lead's pre-registration
> *"least-squares over ALL line correspondences"* (`.claude/journals/lead.md`,
> 2026-09-04, written before any run). Run date **2026-09-04**, commit `b146206`.
>
> **The bar, pre-registered and not restated more kindly here:**
> PASS = median reconstruction **<= 10.0 px@640**; FAIL = **> 13.0 px**, and then the
> joint-correspondence branch **dies on a fit ceiling**; INDETERMINATE = 10.0–13.0.
> Per clip as well as pooled.
>
> Harness: `eval/corr_ls_fit.py`. Results: `data/output/corr_ls_fit.json`.

## The question, and why it is decisive either way

STATE's row records that handed the **TRUE** line-to-model assignment, the joint
correspondence solver reconstructs the court to a median **17.1 px@640**, against the
shipped detector's **8.1 px** on the clips it accepts. The named cause is structural:
the homography is solved from **exactly four line intersections**, so each detected
line's few-px error is amplified where the court is most foreshortened.

Because the test is run **given the true correspondence**, it isolates the **FIT** from
the **SEARCH**. If least squares over every matched line cannot beat an exact 4-point
fit when handed the right answer, then no improvement in correspondence search can
rescue the solver.

## 0. THE CONTROL — the exact-4-point fit, recomputed in this run

**The control reproduces, exactly.** Recomputed in this run, on the same clips and the
same true assignments, the exact-4-point fit's median is

| | |
|---|---|
| **CONTROL, exact 4-point, recomputed 2026-09-04** | **17.10 px@640**, n = 13 |
| quoted in STATE from 2026-08-29 (not used, shown for agreement only) | 17.1 px@640, n = 13 |

Stronger than the pooled agreement: the survivor **set is identical** (the same 13 clip
names), and the **maximum per-clip absolute difference against the committed
`data/output/corr_attrib.json` is 0.00 px**. Arm A of this harness is the 2026-08-29
construction line for line — same frame, same detected lines, same `_match_line`
assignment, same screens in the same order — so the harness is measuring what that row
measured, and the rest of the run is on that basis trustworthy.

## 1. Verdict against the pre-registered bar

# FAIL.

| fit | pooled median px@640 (n=13) | vs bar |
|---|---|---|
| **CONTROL — exact 4-point** | **17.10** | — |
| **LS-geom** — nonlinear LS over all matched lines (the better variant) | **19.80** | **FAIL** (> 13.0) |
| LS-DLT — closed-form dual line DLT over all matched lines | 73.50 | FAIL (> 13.0) |
| (reference: shipped detector on the clips it accepts) | 8.1 | — |

The bar was applied to the **better** of the two least-squares variants, as declared in
§6 before the run. The better variant lands at **19.80 px**, which is not merely outside
the 10.0 px PASS band and outside the 10.0–13.0 INDETERMINATE band — it is **worse than
the control it was meant to beat**. Nothing here is close enough to the bar for the
choice of variant, the pooling, or the population to matter.

Per pool, so a pooled median cannot hide a split:

| pool | n | exact 4-point | LS-geom | LS-DLT |
|---|---|---|---|---|
| TUNE (gold + 1920 refs) | 8 | 19.00 | 23.50 | 123.37 |
| SHELL (held out, 3840) | 5 | 6.39 | 6.79 | 73.50 |

Both pools fail. There is no split in which least squares wins.

**The joint-correspondence branch dies on a fit ceiling — and the ceiling is one stage
further down than "fit" implies.** See §3: it is the *line evidence*, not the fit.

## 2. Per-clip numbers, both fits

All 13 clips on which the true correspondence survives every shipped screen — the exact
population the 17.1 px was measured over. `l/a` = matched lengthwise / across lines;
where that is 2/2 the least-squares problem is exactly determined and *must* reduce to
the 4-point fit, which is an internal control it passes (`CYqapSq5llo`, delta −0.00).

| clip | pool | l/a | exact | LS-geom | delta | LS-DLT |
|---|---|---|---|---|---|---|
| hillsborough_p02 | SHELL | 4/5 | 4.51 | 6.79 | **+2.28** | 119.96 |
| flexi_joy_p01 | SHELL | 4/4 | 4.96 | 3.77 | −1.19 | 9.50 |
| am_classB | TUNE | 2/3 | 5.57 | 22.91 | **+17.34** | 313.80 |
| hillsborough_p08 | SHELL | 4/5 | 6.39 | 6.08 | −0.32 | 18.70 |
| e8T34KoJzOw_s2 | TUNE | 5/3 | 11.96 | 6.67 | −5.29 | 13.91 |
| am_usta45 | TUNE | 4/4 | 12.88 | 9.53 | −3.35 | 16.50 |
| HoHxFSX_gLk_s2 | TUNE | 4/5 | 17.10 | 19.80 | **+2.70** | 268.57 |
| flexi_franz_p01 | SHELL | 2/4 | 20.48 | 77.17 | **+56.69** | 217.20 |
| am_hard_utr | TUNE | 4/5 | 20.90 | 24.08 | **+3.19** | 359.94 |
| flexi_joy_p07 | SHELL | 4/4 | 21.91 | 14.00 | −7.91 | 73.50 |
| CYqapSq5llo | TUNE | 2/2 | 50.49 | 50.49 | −0.00 | 70.30 |
| am_indoor_hard2 | TUNE | 3/4 | 62.04 | 59.85 | −2.18 | 176.43 |
| am_indoor_hard1 | TUNE | 2/4 | 62.95 | 59.72 | −3.23 | 56.11 |

**LS-geom is better on 7, worse on 5, tied on 1.** Paired Wilcoxon over the 12 non-tied
clips: **p = 0.97**. There is no direction here at all — least squares is not a small
win, and it is not a small loss; it is indistinguishable from the exact fit on the
median and *strictly worse in the mean* (27.76 vs 23.24 px) because its failures are
much larger than its wins (`flexi_franz_p01` +56.7, `am_classB` +17.3, against a best
win of −7.9).

**Inspecting the rejects — the five clips LS makes worse.** They are not the clips with
the least evidence. `am_hard_utr` (4/5), `HoHxFSX_gLk_s2` (4/5) and `hillsborough_p02`
(4/5) are among the best-supplied in the set; `am_classB` (2/3) and `flexi_franz_p01`
(2/4) have exactly one extra line beyond the minimum, and on both of those the single
extra line is enough to move the answer 17 px and 57 px in the *wrong* direction. More
line evidence does not monotonically help, which is itself the finding.

## 3. What the line residual says — the ceiling is the LINES, not the fit

This is the part that closes the branch rather than merely failing it. Alongside the
truth error, the harness records the **objective each fit is actually optimising**: the
rms point-on-line distance over every matched line, in px@640.

| homography | median rms line residual (px@640) |
|---|---|
| exact 4-point | 4.18 |
| LS-DLT | 26.73 |
| **LS-geom** | **3.01** |
| **the HUMAN homography (the truth)** | **6.44** |

- **LS-geom fits the detected lines better than the exact 4-point fit on 13 of 13 clips.**
  The optimiser is working; this is not a convergence failure.
- **LS-geom fits the detected lines better than the human court does, on 13 of 13
  clips** — 3.01 px against 6.44 px.

That second row is the whole result. **The detected lines do not agree with the true
court to better than ~6.4 px rms, so the homography that best explains those lines is
not the true court.** Driving the line residual down from 4.18 to 3.01 px moves the
answer *away* from truth as often as toward it, because below ~6 px the fit is
consuming bias in the line detections, not noise. A better fitter converges harder onto
a biased target.

So the failure is not "four points is too few". Least squares over all the lines is the
strictly better fitter by its own objective and it does not help, which means **the
error budget lives upstream of the fit, in the line detections themselves.** No fitting
strategy — 4-point, all-lines, or anything between — can recover a court the line
evidence does not contain.

Caveat, stated rather than buried: the "truth" is the human's four clicks, and
`eval/score_truth.py` records that the clicks are a sample from a ~5.8 px neighbourhood
rather than the best-registered court. That inflates `rms_truth` somewhat. It does not
rescue the conclusion — 6.44 px is the same order as that neighbourhood, which only
sharpens the point that the fit is being asked to resolve differences smaller than the
evidence supports.

## 4. Method, and the one variable

Both arms run inside a single function on a single frame, from a single call to
`cf._precompute`. **Same clips, same frames, same detected line set, same `_match_line`
true assignment, same shipped screens in the same order.** The only thing that differs
is how the homography is computed from that assignment.

- **Arm A, exact 4-point (the control).** `corr_attrib.trace`'s construction, unchanged:
  the extreme matched lengthwise pair and the extreme matched across pair, their four
  intersections, `calibration.compute_homography` on four points.
- **Arm B, LS-DLT.** The dual line-correspondence DLT: `l_w ~ H^T l_i` for every matched
  line, two independent equations per line from the cross product, conditioned on both
  sides, null vector by SVD. Closed form, init-free.
- **Arm B', LS-geom.** Nonlinear least squares on the **geometric point-on-line distance
  in pixels**, over every matched line. Started from **both** the dual DLT and the exact
  4-point fit, keeping whichever run reaches the **lower objective** — objective only,
  never truth, so no leak, and deliberately generous to the hypothesis.

**A broken first attempt, recorded because it is the same trap the 17.1 px row is
about.** The obvious point-on-line residual — project the world *endpoints* of each
court line and measure their distance to the detected line — is unusable on this
footage. A low mount puts the far baseline at or beyond the vanishing line, so a world
endpoint projects with a near-zero or sign-flipped depth and the distance explodes: on
`hillsborough_p02` that objective scores **204 px@640 under the human homography**. An
objective the true answer does not minimise cannot test anything, and it was discarded,
not tuned. The formulation used instead runs the other way — project the *model line*
into the image (`l_i = H^-T l_w`, a linear map of a line, no division by depth) and
measure the distance from sample points on the **frame-clipped detected line**, which
are real image points inside the frame and sample the line only where it was actually
seen. Acceptance test for the objective itself: rms under the human homography must be
a few px, not 200. It is 2.5–19.8 px across the 13 clips.

Assignment fidelity is **recorded, not repaired** (rule 9): where two model lines match
the same detected line, `dup_len` / `dup_acr` in the JSON say so. It occurs on the
across family of 7 of the 13 clips and never on the lengthwise family; the duplicate
constraint was left in, because removing it would be a second variable.

## 5. Provenance

- **Commit** `b146206`. Harness `eval/corr_ls_fit.py`; raw rows `data/output/corr_ls_fit.json`.
- **Clips:** the same 40 sources `eval/corr_attrib.py` used — `eval/score_truth.py`'s
  `truth_sources(frames=1)`, 20 court-gold clips + 20 reference clips, first frame with
  all four doubles corners labelled. Survivors n = 13 (8 TUNE, 5 SHELL).
- **Ground truth is human only:** per-frame clicks for the gold clips, `"_exact": true`
  hand placements for the references. `eala_pts_auto.json` is excluded by the loader
  (scoring against a detector's own output is self-grading). `mpc_tuesday_p01/p07` are
  excluded from truth entirely — their two independent labels disagree by 25.4 px@640 —
  and they die at `camera re-fit` in any case.
- **Resolutions:** 4 gold at 640x360, 4 references at 1920x1080, 5 at 3840x2160. All
  errors are reported at **px@640** via `scale = 640/w`, as in the original row.
- **Deterministic:** no seed is involved. There is no sampling, no RANSAC in either fit
  arm, and no model inference; `find_pencils` runs identically in both arms and is used
  only for the survival screen, not for the fit.
- **Reproduce:**
  `backend/.venv/Scripts/python.exe eval/corr_ls_fit.py --json data/output/corr_ls_fit.json`
  (40 clips, 11 s).

## 6. Declared BEFORE the run: which least-squares variant the bar is applied to

Two implementations of "least squares over all matched line correspondences" are
computed, and **both are reported** (LS-DLT and LS-geom, defined in §4).

**The pre-registered bar is applied to whichever of the two is BETTER.** That is
deliberately generous to the hypothesis, and it was declared before the numbers existed,
because the actionable outcome of this run is a FAIL — and a FAIL measured against the
*best* least-squares variant is the one that actually closes the branch.

## What this does and does not close

**Closes:** *"the 17.1 px ceiling is caused by fitting from only four intersections."*
It is not. Using every matched line, with a fitter that provably reduces the line
residual on 13 of 13 clips, leaves the reconstruction at 19.80 px. **The joint
line-to-model correspondence branch dies on a fit ceiling** — and §3 locates that
ceiling in the line detections, one stage upstream of the fit.

**Follows from it, and is the actionable half:** the solver's other two failures are no
longer worth paying for. C6's 12.6x cost and the 22-of-30 that die before scoring are
both problems of the correspondence **SEARCH**. This run was designed so that its answer
governs them: with the search perfect — the true assignment handed over — the fit still
lands at 17–20 px against the shipped path's 8.1 px, so **no amount of search
improvement reaches the accuracy bar.** Fixing C6 or the 22-of-30 would buy a solver
that finds the right answer and then still reconstructs the court twice as badly as what
ships.

## NOT ESTABLISHED THIS RUN

- **Why the detected lines carry ~6.4 px rms bias against the human court.** §3 shows
  the error budget is upstream of the fit; it does not decompose that budget between
  line-detector bias, the human clicks' own ~5.8 px neighbourhood, and lens/roll. That
  is the question a continuation would ask, and it is about the **line detector**, not
  about correspondence.
- **Weighted least squares.** Every matched line is weighted equally here. `lines`
  carries a per-line weight and it was not used, on the one-variable rule. Given
  p = 0.97 and a 6.4 px evidence floor, a reweighting is not a plausible route from
  19.80 to 10.0, but it is untested and is not claimed as tested.
- **Whether the shipped 8.1 px path would also degrade under this objective.** The 8.1
  px figure is quoted from STATE for orientation only and was not recomputed here.
- **The correspondence SEARCH** — C6's 12.6x cost and the 22-of-30 kills. Explicitly out
  of scope for this run; see above for why the result governs them anyway.
