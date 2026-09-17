# Joint line-to-model correspondence — the pre-registered gate

> Evidence for the `court-correspondence-gate` row in [docs/STATE.md](../STATE.md) (Open).
> **Written 2026-08-27, BEFORE any code.** Nothing here may be loosened after a
> result is seen (hard rule 2). A failed gate stays failed.

## What is being built, and why this one is not a sixth re-tune

Session P closed court auto-detection with an unusually specific characterisation:

> **The detector FINDS the court's lines** — the four outer lines sit a median
> **1.3–4.1 px@640** from a detected line and are present on **27–38 of 40**
> clips — **but it cannot assemble them into the court.**

Five branches have been measured and none survives: reach, the prior weight,
`topk`, line-construction, line-snapping. All five share one assumption — that
the assignment of *which detected line is which model line* can be settled
**before** the homography is solved. Every one of them guesses the assignment
first and then optimises, and the guess is what fails:

- **Line-construction** picked 2 baselines + 2 sidelines by direction family.
  Wrong in principle: under perspective the two doubles sidelines converge, so
  they form no angular cluster. 24 of 26 lines landed in one family on
  `am_hard_utr` while both true sidelines sat in the detected set at 0.1 and 2.2 px.
- **Line-snapping** matched the four model lines independently, which lets them
  pick a mutually inconsistent set. Median distance from truth: seed 9.8 →
  refiner 8.4 → **snap 70.5**.

**Joint correspondence solves assignment and homography together** — the
Farin-style formulation the cross-ratio screening was originally deferred for.
It is a different algorithm, not a re-tune of the lattice, and it is the one
thing Session P explicitly said was **NOT tested**.

## Baseline, so the bars mean something

| quantity | current |
|---|---|
| gold clips auto-accepted (Tier 1 consensus, ≥6 of 8) | **12 of 20** |
| precision record of those accepts | **zero wrong courts ever accepted** |
| median error on accepted clips | **8.1 px** |
| nearest lattice point to truth | **7–20 px** |
| refiner moves AWAY from truth | **17 of 38** clips, median landing 14.1 px |
| criteria recognise the correct court when handed it | **19 of 20** (Session O) |
| reference clips (1920) auto-accepted | **2 of 20** |
| shell clips (3840) auto-accepted | **0 of 10** |

Scoring is **not** implicated — Session O measured that. Do not spend on the
criteria.

## The gate

Measured on the **20-clip court gold set** with `court_split.json` enforced
(`assert_no_court_gold_leak`), plus the 10 shell calibrations and the reference
clips. Report all three pools separately; never pool them into one percentage.

**C1 — precision is inviolable.** **Zero wrong courts accepted**, on every pool.
The current accept path has never once accepted a wrong court, and that record is
worth more than any recall gain. One wrong accept fails the gate outright,
whatever C2 says.

**C2 — accepts must rise.** Gold **12 of 20 → ≥15**. This is the headline and it
is deliberately not "improves": three clips is roughly the number the lattice
gap could plausibly be costing, given the true lines are 1.3–4.1 px from a
detected line on nearly every clip.

**C3 — accuracy must not degrade on clips that already work.** Median error on
the currently-accepted 12 must stay **≤ 8.1 px**, and no individual clip may get
worse by more than **3 px**. A method that trades existing accuracy for new
accepts is not an improvement.

**C4 — it must reach the pools the lattice cannot.** At least **one** of:
references 2/20 → ≥4, or shell 0/10 → ≥2. Gold alone is 640-wide and the
resolution-dependent failures live in the other two pools.

**C5 — the mechanism must be shown, not inferred.** On at least 3 clips where the
lattice's nearest point is >10 px from truth, report the correspondence the
solver chose and confirm it matches the true assignment. *"It got closer"* is not
evidence the assignment was solved — that is trap **T19**'s shape (a rate is not
an association).

**C6 — cost.** No worse than **5× per-clip** wall clock against the current
consensus path. `topk` was killed for 7× at zero gain; a correctness win may
fairly cost more than a null one, but it has to be stated and bounded.

## Stopping rule

**If joint correspondence lands the true assignment (C5) and accepts still do not
reach 15 of 20, then assembly is not the binding constraint either, and court
auto-detection closes for the third and final time** — with the honest conclusion
that single-camera amateur court detection is a manual-calibration problem, and
the effort moves to making that path fast rather than making detection work.

This is the sixth branch. It is not open-ended.

## What must not happen

- **No new scorer.** Session O settled that the criteria recognise the right
  court on 19 of 20. Use the shipped ones (T15, T04).
- **No lowering the 6-of-8 consensus bar.** Measured, failed: the single 5-vote
  clip is wrong by 68.7 px.
- **No CourtNet.** It is Tier 2 and `courtfit` consensus beats it; that is a
  recorded dead end.
- **No touching `AGREE_PX`** as part of this. It is 6× tighter on 4K than on the
  gate and is doing a second job — a real issue, but it cannot ship before the
  search problem and must not be folded into this experiment as a second variable.

---

## Step 1 — grouping by CONCURRENCY: measured 2026-08-29

The gate says all five failed branches assumed the assignment can be settled before
the homography. The first thing joint correspondence needs is the primitive that
killed the last one: **which detected lines belong to the same world-parallel
family.** P3a answered that by direction and it was ill-posed under perspective.

`eval/pencils.py` answers it by **concurrency** instead. World-parallel lines meet at
a shared vanishing point whether or not they look parallel, so a family is a *pencil*
— a set of lines sharing a null vector. Staying in homogeneous coordinates
(`l = (cos n, sin n, −rho)`, membership iff `l·v = 0`) handles a vanishing point at
infinity with no special case, which a square-on court genuinely has.

### The bar failed first, and that stands

Pre-registered: *the true lengthwise family and the true across family land in
different pencils, on a majority of clips.*

| run | result |
|---|---|
| as first written (`tau` = 0.012, greedy exclusive membership) | **15/38 — FAILS** |
| after fixing greedy exclusivity (a correctness fix, see below) | **19/38 — FAILS** |

**Greedy exclusive membership was a genuine defect, not a knob.** Pencils are found
largest-first, and in a cluttered frame the largest concurrent family is the
building — so it consumed court lines before the court's own pencil could form.
The tell: capture of the true lines was pinned at 2.0 of 3.5 whether 2, 4 or 6
pencils were extracted. Exclusivity is a decision about which family a line belongs
to, and a greedy pass is not entitled to make it; the correspondence stage has the
court model and can.

### What was actually binding: the inlier tolerance

`INLIER_TAU = 0.012` was a guess — about **0.7°** of pencil misalignment, against
detected lines whose angular error `_structure` itself allows **7°** for. Sweeping
it, with `tau` chosen on the TUNE pool and shell **held out** per the tuning rule:

| `tau` | ≈ angle | TUNE (gold + 1920 refs) | SHELL (held out) |
|---|---|---|---|
| 0.012 | 0.7° | 11/30 | 6/8 |
| 0.020 | 1.1° | 20/30 | 7/8 |
| **0.030** | **1.7°** | **21/30** | **7/8** |
| 0.045 | 2.6° | 21/30 | 7/8 |

Not monotonic in the earlier full-pool sweep (0.03 → 28/38, 0.06 → 26/38), so this is
an optimum rather than "looser always wins". `min_pencil` was changed alongside `tau`
in the first sweep — a two-variable slip — and was isolated afterwards: **2 and 3 give
identical results**, so the gain is attributable to `tau` alone.

### Where this leaves the build

**The primitive works.** On the held-out shell pool the two court families separate on
**7 of 8** clips — the pool where the angular split had put 24 of 26 lines in a single
family. Concurrency grouping is the right operation, and it is now measured rather
than argued.

**Nothing in C1–C6 has been touched.** This is step 1 of the build, not the gate. What
remains is the part that makes it *joint*: enumerating assignments of pencil members
to the model's known positions (lengthwise x = 0, 1.37, 5.485, 9.60, 10.97; across
y = 0, 5.485, 11.885, 18.285, 23.77), screened by **cross-ratio** — the projective
invariant that is equal in the image and in the metric court, and the reason
cross-ratio screening was deferred in Session O for want of a generator. That
generator now exists.

---

## Step 2 — the joint solver: SUB-BAR FAILED, and C6 failed with it. Run 2026-08-29

`eval/correspondence.py`. Two lines from each pencil, labelled against the model's
known positions, homography solved exactly from the four intersections, scored with
the shipped criteria. The labelling **is** the assignment, so assignment and geometry
are chosen together — the thing all five earlier branches did not do.

Two lines per family rather than four, because step 1 measured capture at a median
2.5 of 3.5 lengthwise: a strict cross-ratio needs four collinear points and would
have refused most clips before starting.

### A circular-scoring bug had to be fixed first, and it is worth recording

The first version scored candidates on `_ori_detail` + `_structure` alone. That is
**circular**: the hypothesis is built from four detected lines and both criteria
reward landing on detected lines, so the four that constructed it match by
construction. Measured — a labelling of two far-apart sidelines as `x=0, x=1.37`
scored **g = 1.00, st = 1.00** while sitting **2,245 px from truth**; the enormous
stretch throws the rest of the court off-frame and neither term objects.

Applying the full shipped accept path (pose prior, `verify_court`, `_cam_refine`)
is what discriminates. All are shipped criteria, so the C-list permits them.

### The result

Pre-registered sub-bar: *best-scoring candidate within 20 px@640 of the human court
on a majority of the TUNE pool.*

| pool | clips | produced any candidate | top-scoring ≤20 px |
|---|---|---|---|
| TUNE (gold + 1920 refs) | 30 | **17** | **7** |
| SHELL (held out) | 8 | **2** | **0** |

**7 of 30 on TUNE — the sub-bar FAILS** (a majority needs 15). For scale the shipped
lattice path accepts 12 of 20 gold.

**The dominant failure is not mis-ranking, it is producing nothing at all.** 13 of 30
TUNE clips and 6 of 8 shell clips yield zero surviving candidates. Only **1 of 19**
clips that did produce candidates had a good one ranked below a bad one
(`flexi_joy_p07`). So the scorer is not the problem here either — consistent with
Session O, and not a new claim.

`am_ntrp40` is the sharpest case: the shipped detector **accepts** it at 7.9 px, and
the joint solver produces **no candidate whatsoever**. Whatever is filtering, it is
filtering out courts that demonstrably work.

### C6 — cost: FAILED

**907 s for 40 frames = 22.7 s/frame against a 1.8 s baseline = 12.6×.** The gate caps
cost at **5×**, and killed `topk` for 7× at zero gain. C6 fails as implemented.

### Where this leaves the branch

The gate's stopping rule is conditioned on C5 + C2 and has **not** fired: C1–C5 are
unmeasured, because a solver that produces nothing on 19 of 38 clips cannot be run
through them honestly.

What is established: the joint formulation is expressible and, where it produces a
candidate, it usually produces a *sensible* one — `am_hard_utr` at 13.8 px labelled
`x = 9.60, 1.37 | y = 0.0, 5.5`, correctly identifying that it found the two singles
sidelines with the near baseline and near service line. That is the C5 shape of
evidence, on the clips that survive.

What is not established, and must be diagnosed before any further build: **which
term is discarding the true court on the 19 clips that return nothing.** The
candidates are the two expensive screens added to fix the circular scoring
(`verify_court`, `_cam_refine`), the quad convexity/floor screens, or the pencils
themselves failing to supply two usable lines in each family. That is an attribution
question of exactly the shape `eval/seed_reach.py` answered for the lattice, and it
should be answered the same way rather than guessed at.

## Step 3 — attribution: three of my own screens were wrong, and the ceiling is 17 px

`eval/corr_attrib.py`. Hand the solver the correspondence the HUMAN homography says
is correct — real detected lines, real model labels — and follow that one candidate
through every screen. Not a search result: the answer. Whatever kills it is
discarding the truth.

### Two self-inflicted screens, found and removed

| | TUNE kills |
|---|---|
| size floors on the **construction quad** | mis-labelled as the cause; removing them changed nothing |
| **convexity** of the construction quad | 10 |
| **convexity** of the projected corners | 11 (the same clips, one stage later) |

The size floors belong on the projected court, not on the four intersections: label
two lines `x=0` and `x=1.37` and they bound a legitimately narrow 1.37 m strip.

Convexity was the real defect, and it is wrong **everywhere**. A homography preserves
convexity only when the shape stays off the vanishing line — and a low mount puts the
far baseline on it, so the correct image of the court is *non-convex*. Removing it
from the construction quad alone moved the kill one stage later without saving a
single clip (10 "not convex" → 11 "corner screen", survival flat at 7/30), which is
what proved the projected court is the non-convex thing. `autodetect`'s own
degeneracy floor checks width and depth and nothing else; the solver now matches it.

### What remains, after the self-inflicted screens are gone

| stage | TUNE (30) | SHELL (8) |
|---|---|---|
| **SURVIVED** | **8** | **5** |
| `verify_court` | 9 | – |
| pose prior | 5 | 1 |
| pencil supply (too few court lines detected) | 4 | – |
| two pencils (families not separated) | 2 | – |
| `_cam_refine` | 2 | 2 |

**The kills are now spread across SHIPPED criteria rejecting a correctly-labelled
court** — `verify_court` on 9 of 30 being the largest. This is not new: the candidate
audit already found `verify` blocking the human court on 4 of 10 references. It does
mean no single change rescues the solver, which is the test this script was written
to apply.

### The accuracy ceiling — and why C3 would fail anyway

**Where the true correspondence survives every screen, the reconstructed court is a
median 17.1 px@640 from truth** (n = 13), against the shipped detector's **8.1 px**
median on the clips it accepts. C3 requires median ≤ 8.1 px and no clip worse by more
than 3 px, so **C3 fails even when the correspondence is handed over correct.**

The cause is structural: the homography is solved from exactly four line
intersections, so each line's few-px error is amplified at the far end where the
court is most foreshortened. Two continuations are untested and both are real:

1. **Least-squares over ALL matched line correspondences** rather than an exact fit
   to four points. Cheap, and aimed squarely at the 17.1 px ceiling.
2. **Why the shipped screens reject a correct court** — `verify_court` on 9 of 30 is
   its own question, and one that touches the shipped accept path rather than this
   solver.

Neither is attempted here. C1–C5 remain unmeasured end-to-end; C6 failed at 12.6×.
