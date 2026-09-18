# Decisions — the court feature

**Scope reduced to the court feature by the founder, 2026-09-17.** Every earlier entry — ball,
bounce, line calls, occlusion, capture visit, spec contradictions for the ball path, SwingVision's
ball levers — is preserved in `swingpath:docs/archive/2026-09-17-pre-court-only/docs/DECISIONS_PENDING.md`.
**Archived, not open.**

**How this file works:** batch founder asks into ONE update. Do not interrupt for them one at a time.
Each open entry says what is blocked, what it costs to unblock, and what is being done meanwhile.

---

## RULINGS ON RECORD (founder, 2026-09-17) — binding, do not reopen

1. **Court work only.** "Continue - remember only court related things." And: "Clear out ALL OTHER
   FEATURES aside from the court - save the information that has already been doen but all
   instruictioins aside from this court feature needs to be wiped from MD files so we dont randomly
   work on it."
2. **The court is found AUTOMATICALLY.** "dont use finger level accuracy - I keep saying that it must
   be the machine learning the 3d space and determining the far and close lines and assuming where
   the end points are if they are not visible similar to swing vision".
   - This settles the 2026-09-09 open item, "a court model trained on AMATEUR low-mount footage, on a
     leak-clean split — founder call".
   - It overrides the 2026-09-05 conclusion that manual setup is the product answer.
3. **Live court tracking continues when the phone moves.** "must continue, its essentially live court
   tracking so the app should know that the court is still there but just shaped differently because
   the phone moved". Re-fit, never refuse, never ask for a re-tap.
4. **Indoor shell courts are in scope** ("yes"). The old shell blocker (a SEARCH failure) does not bar
   the feature; it is a hard case the automatic finder must handle.
5. **The 2026-09-06 court-gold edits (commit `2e49f38`) were the founder's.** They stand; no re-score.
6. **No court visit is possible yet** ("can not do yet"). Long far-end tape strips are approved in
   principle but cannot be done in person. No metric real-court truth is available for now.

---

## OPEN — waiting on the founder (court only)

### A. The drift numbers in SPEC §1 (15 px, 10 s, 6/8) — NOT ready to decide yet

- **The issue:** these were set for a different mechanism. 15 px is ~5 m at the far
  baseline at 1080p / 3 m; a court good to 5 cm needs a re-fit tolerance of ~0.1 px on far lines. The
  phone's motion sensor cannot see drift that small, so the research note recommends both an IMU bump
  trigger and a periodic image re-fit.
- **What unblocks it:** CP1 (whole-court fit precision), then a tracking test under simulated phone
  movement. Bring the founder a measured number, not an estimate.
- **Meanwhile:** CP1 is running.

### B. A blind click set for real-footage court checks (lower priority)

- **The issue:** the court gold's non-corner keypoints were computed from four clicks, so real footage
  has no independent check of line placement. A real check needs the founder to click T-junctions and
  service-line junctions directly, with no overlay, on ~20 frames. That needs a new tool mode and a
  pre-registered bar first; it is not built.
- **Why it waits:** human clicks (~17 px at 1080p) are far too coarse to settle sub-pixel precision.
  They can only catch gross real-world failures such as lens distortion or non-regulation courts.
- **Meanwhile:** nothing is asked of the founder.

---

# PM feasibility check: the founder's per-frame roadmap (2026-09-18)

**The call in one line:** three of the four items are buildable; **item 1's Tier 1 is not the court —
it is a seed**, and saying otherwise is contradicted by a measurement we already own. Items 1 Tier 1
and 2 are **the same deliverable** (one amateur-trained model), so the roadmap's four items are three
builds. Nothing here is blocked on new footage; most of it is blocked on one model that does not exist
and on one founder ruling that the roadmap itself asks to suspend.

Every number below is cited to the file that owns it. Every judgement is labelled as a judgement with
a confidence.

---

## (a) Item by item

### Item 1 — two-tier neural + photometric, per frame

| Half | Verdict |
|---|---|
| **Tier 1 as the SHIPPED camera** (a network predicting extrinsics/intrinsics directly) | **CONTRADICTED BY A MEASUREMENT** |
| **Tier 1 as a SEED for a line measurement** | **FEASIBLE-WITH-CONDITIONS** — and this is the same model as item 2 |
| **Tier 2, a fast paint fit (<5 ms)** | **NOT YET** — the speed claim is unmeasured and the algorithm question comes first |
| **The stateful fallback** | **A FOUNDER DECISION, not an engineering one** — see F1 |

**Tier 1 cannot place a line to 5 cm. Plainly: no.** This is not an opinion about network capacity, it
is arm K0, already run. `evidence/court-camera3d.md` §G2 took 21 noisy court keypoints through PnP to a
camera with **no paint fit** and measured the far baseline at **p90 6.65 m** and the far service line at
**3.86 m**, against a 5 cm target — KILL by a factor of about 130. `evidence/court-map-ceiling.md` (C1)
says why: a court pinned by POINTS misplaces far lines by metres unless those points are right to
~**0.1 px** at 1080p / 3 m, **whoever or whatever finds them, an ML model included**. Hard rule 5 says
the same thing structurally — a single camera does not observe depth, it imposes it, so whatever fixes
the depth parameter is what sets the far-line error. **A network that outputs camera parameters is a
point-like estimate.** It never measures a line.

The size of the gap is worth stating, because it is the whole argument: on its *correct-camera* trials
arm K's paint fit holds focal length to **p90 0.043%** and camera height to **p90 0.6 mm**
(`evidence/court-camera3d.md` §G1). That is the precision a direct regressor would have to match to
replace it. Sub-millimetre height regression from one frame is not a thing anyone has shown. *Judgement,
confidence 0.9.*

**What would have to be true for Tier 1 to be worth building:** only that it is a good enough SEED. Arm
K measured exactly what "good enough" means — the seed's height error predicts the failure: **0.69 m on
the 35 wrong-camera trials against 0.13 m on the rest**, focal 10.5% against 4.6%. So Tier 1's job is
"get within ~0.15 m of the right height", not "be the answer". That is a completely different, and much
easier, target. It also means **Tier 1 must never be allowed to emit a court** — its output should be
typed as a seed in the code so no later change can quietly ship it.

**Tier 2 is where the whole thing lives, and its cost claim is the roadmap's weakest number.** Measured
this session at 1080p on desktop CPU: **full paint fit 9.6 s, tracker step 0.020 s, `paint_check`
0.003 s.** The proposal asks 9.6 s → 5 ms, about **1,900x**. Coarse-to-fine on a GPU is a real lever and
I am not calling it impossible, but note the shape of the existing numbers: **the 0.020 s path is the
warm, seeded one and the 9.6 s path is the cold one.** The cheap path we already have is the one that
uses the previous frame. That is not a coincidence and it is the crux of F1.

**Two conditions before any Metal work.** (i) Prove on desktop, in Python, that a pyramid / reduced-
iteration schedule *keeps* arm K's per-line p90 — one variable, same 400 seeds. (ii) Get one real device
timing (F3). Porting an optimiser to Metal before knowing whether the cheap version still holds 5 cm is
the most expensive possible way to discover it does not.

**One precision trap in Tier 2, named so it cannot be designed in:** the far baseline's entire margin is
**~1.4 cm** and the libx265 codec already spends **2.65 cm** of it (`evidence/court-fit-cp1.md`, qa
audit). Coarse pyramid levels may seed, but **the final measurement must be taken at native resolution.**
A fit that terminates on a 1/2 or 1/4 level will not hold 5 cm on the far lines.

### Item 2 — the amateur keypoint failure

**FEASIBLE-WITH-CONDITIONS, and it is the item that unblocks the other three.**

The measurement that decides it is `evidence/cnn-global-classical-local.md`: on amateur footage only
**2–3 of 14** CourtNet heatmap peaks clear 0.40, `detect_court_learned` returned `None` on all 8 frames
of 4 of 6 probed clips, gold went **12/20 → 2/20** and shell **20/80 frames → 0/80**. Its stated
mechanism — *"not a tunable threshold; the upstream BROADCAST checkpoint does not see these courts"* —
is precisely an argument **for** retraining, and that row's own open item ("a CourtNet trained on
AMATEUR low-mount footage, on a leak-clean split — founder call") is the thing the founder chose on
2026-09-17. Item 2 is the sanctioned route, not a re-proposal.

Conditions, in order of how likely each is to bite:

1. **Score it as a SEED, never as a court.** Its floor is seed quality (§d), not pixels. This collapses
   the difficulty and it is legitimate because the paint fit decides the camera.
2. **It may not be trained or scored against the gold pool's non-corner keypoints.** Those are
   `applyH(H, ...)` of four human clicks (`evidence/court-map-gold.md`, P8 C2 — returned VOID, not a
   pass). Scoring a keypoint model against them grades a homography against its own output (hard rule 1)
   and would burn a one-way TEST pool (hard rule 4).
3. **Synthetic-first is the only leak-clean source with exact labels**, and we own the renderer. Real
   footage's role is then **availability** validation (how many keypoints fire, does the seeded fit
   lock), which needs no precise labels at all. See F5 for the sim-to-real risk.
4. **Geometric augmentation over colour jitter: agreed, cheap, low risk.** *Judgement, confidence 0.75.*
   It is the right prior for foreshortening. Not a decision that needs a founder.

**The half of item 2 I would change: net-guided seeding.** "Solve the pose from the near baseline plus
the net" has been built and falsified here. `evidence/net-baseline-solve-without-far-line.md`: the
geometry is exact (0.007 px median far-baseline row from TRUTH observables on all 40 clips) but from
*detected* lines the far **corner** lands **17.4 px@640** against an 8.1 px bar, because near-baseline
**width** measures 12.44 px and width at the net 44.63 px — a width is two oblique intersections, not a
row. And the net **ground** line is not paint: found on 24/40 versus the tape's 38/40, and substituting
tape for ground moves the far baseline **32 px**. **As a precision route it is contradicted by a
measurement.** But the same file measured a by-product that is worth more than the route: **camera
height survives a 40% standoff error** (1.64 → 1.62, 2.11 → 1.95, 2.88 → 2.92 m). A height estimate good
to a few centimetres is **exactly the seed quality arm K needs**, and it feeds item 3's anchors. So:
**keep the net solve as a height-prior generator, drop it as a pose solver.** *Judgement, confidence
0.7.*

**The consequence three steps out that the founder must see.** Below ~**2.0–2.2 m** of mount height the
net tape does not merely obscure the far baseline, it **overlaps** it — the two are unseparable because
the information is not in the image (`evidence/setup-envelope-net-occludes-far-baseline.md`; the
crossover is stable across 2–5 m standoff, 65–100° and 720p/1080p, because it is set by the net's
0.914 m against the far half's depth). **Every amateur mount we own is below it**: `yt_match40` 1.64 m,
`am_hard_utr` 1.74 m, `demo30` 1.38 m, `flexi_joy_p01` 1.36 m; the best census clip, `sAjkpeRq4P4`, is
3.33 m (`evidence/capture-floor-census.md`). So an amateur model trained on our own footage would be
trained largely on frames where the far baseline is **not observable at any precision**. No augmentation
fixes that. It is decision **F2**.

### Item 3 — the 8.75% wrong camera

**FEASIBLE-WITH-CONDITIONS on the multi-anchor half. The net-clearance half as written is CONTRADICTED
BY A MEASUREMENT and must be rewritten before it is built.**

**Multi-anchor is aimed at the right target.** The measurement it attacks is arm K's, and the roadmap
reads it correctly: 35/400 = 8.75% wrong cameras, f 13–130% off, **discrete basins, not noise** (f −13.7%
with height 3.39 m recurs 5 times; ±15.4% recurs 4 times), predicted by seed height error
(`evidence/court-camera3d.md` §G1). Launching 2–3 fits from fixed height priors is a direct attack on a
measured cause. Cost is 2–3x the fit — irrelevant at one-time setup, fatal per frame, which is another
reason setup and tracking should not be forced into the same budget.

**The condition is the selector, and it is unmeasured.** "Select the lowest photometric residual"
assumes the cost function separates the 35 wrong cameras from the 365 right ones. **Nobody has checked.**
Hard rule 5 is explicit that a reprojection residual certifies nothing, and G3 measured the live version
of that failure: a tracker whose drift test compared its pose against its own flowed points **agreed
with itself while every point sat on the wrong line**, reporting `tracking` while 7–10 m out for 50
frames. A photometric cost against image paint is a genuinely different object from a self-consistency
residual and may well separate them — but **it is a hypothesis, and it is testable today on data we
already have.** That is the first thing to build (§c).

**The net-clearance check as written would reject correct courts on every mount we own.** "Invalidate any
solution that places the tape below or overlapping the far baseline" is false as a rule: below ~2.2 m,
**a correct solution overlaps.** Written that way it would false-reject the 1.36–1.74 m class, which is
our entire amateur corpus. **The rewrite:** compare the *predicted* tape/baseline relationship at the
fitted camera height against the *observed* one — a solution is invalidated when it disagrees with the
image, not when it overlaps. Also cap the ambition: the tape's per-pixel sensitivity is **3.2%/px at
720p**, so the whole 10% agreement bar is ~3 px of tape row
(`evidence/net-tape-camera-height-consistency.md`), and net sag is a real court-specific confound.
**It is a gross-error gate, never a precision term.** Separately, do not substitute the net POST: posts
are CLOSED (3 of 11 = 27% against a 67% bar, `evidence/net-post-detector.md`). The tape is the one
off-plane reference that has ever worked here (13/15 within 10%).

### Item 4 — large-knock recovery and far-line blind spots

| Half | Verdict |
|---|---|
| **Multi-scale paint-contrast checking** | **FEASIBLE** — cheapest item in the roadmap, with one mandatory negative control |
| **Detector-free local recovery** (already on dev seeds) | **FEASIBLE NOW** — exists unscored; score it |
| **Global neural re-localisation** | **NOT YET — blocked on item 2.** The detector does not exist |

Multi-scale checking attacks a named failure (thin foreshortened far lines lost to compression noise)
and `paint_check` costs **0.003 s**, so the budget argument is trivial. **The risk is the direction
nobody states:** downsampling makes a *neighbouring* line look like the right one, and G3 proved a
confident wrong lock is the worst outcome this system can produce. So the gate must include the
negative control — on a court displaced onto an adjacent line, does the multi-scale check still say "not
locked"? *Judgement, confidence 0.8, that it passes; the control is mandatory regardless.*

Global re-localisation is exactly what founder ruling 3 demands (re-fit, never ask for a re-tap) and I
support it — but it inherits item 2 entirely, and `evidence/court-camera3d.md` already recorded the
rule that must survive it: **recovery must not depend on a detector existing.** The dev-seed work built
that detector-free path (pose-only re-fit, 40 px first pass; 1-frame recovery from a small knock, but a
**~4x knock is lost and never recovered**). Build both layers, in that order: the detector-free path is
scorable now, the neural path is not.

---

## (b) The rule-3 check against `docs/court/CLOSED.md`, branch by branch

I checked all 22 rows. Fifteen touch nothing in this roadmap: detected-line quad construction, `topk`,
pose-prior ablation, `EVID_BAND`, behind-camera projection, the `tol` sweep, both player-foot rows, the
far-player motion gate, `AGREE_PX` widening, gravity/arc, the 6/8 → 5/8 consensus row, and the
single-frame auto-seed row are all about mechanisms no item proposes. The seven that do touch it:

| Closed branch | Which item resembles it | How it differs — and what must be pre-registered |
|---|---|---|
| **CNN-global → classical-local** (FAILS; premise supported, remedy unavailable) | **Item 1 in full, and item 4's global re-loc.** This is the closest match in the file and must be handled carefully | The verdict killed **the remedy, not the architecture**: the CNN refused because *the upstream broadcast checkpoint does not see amateur courts*, and where it did fire the local-refine claim reproduced (7.2 → 5.9 px, n=1). Item 1 differs on the exact axis that killed it — **a model trained on amateur/synthetic low-mount data**, which that row itself names as the open founder call — and the local stage is a **3D whole-court paint fit**, not a 2D classical refine. **Consequence: item 1 is a closed branch with its named blocker removed, which is only legitimate if item 2 succeeds first.** That is a sequencing fact, not a caveat |
| **Court AUTO-detection generally** (CLOSED for v1; reopened as a GOAL by the founder 2026-09-17) | All four items | The row's own text sets the test: a new automatic route **must differ from the branches it names**. Items 1/2/4 differ by being learned-from-amateur-data seeds feeding a paint fit; item 3 differs by attacking basin selection, which no closed branch addressed |
| **Least-squares over ALL matched line correspondences** (19.80 px vs a ≤10.0 bar) | **Item 1 Tier 2** | That branch fit to **detected line primitives**, whose ~6.4 px disagreement with truth was the ceiling — *"a better fitter just converges harder onto a biased target"*. The paint fit has **no line-detection stage**; it measures paint intensity directly. CP1 and arm K price that difference at roughly two orders of magnitude. Allowed |
| **Snapping a near-correct court onto detected lines** (seed 9.8 → refiner 8.4 → **snap 70.5**) | **Item 1 Tier 2, item 4's local search** | Differs by being a **jointly parameterised whole-court fit**, not per-line nearest-neighbour association. **Pre-register this explicitly**: if a "shallow" pyramid fit degenerates into independent per-line snapping to save iterations, it *is* the closed branch and it will land at 70 px |
| **Observability from geometry instead of nearby paint** (+0.000 margin) | **Item 3's net-clearance check** | Differs by using an **off-plane physical object** (tape at 0.914 m) rather than ground-plane geometric observability — and `evidence/independent-calibration-references.md` found the off-plane/ground-plane split is precisely what separates the checks that worked from the ones that did not. Allowed, but the +0.000 precedent sets the bar: it must separate the known 35 wrong cameras or it is not built |
| **Net POST and fitted-hfov as calibration references** (3 of 11 = 27% vs a 67% bar) | **Item 3's net constraint** | Differs by using the **tape**, not the post. Tape passed (13/15 within 10%); post failed and is confidently wrong on 4 of 11. Allowed **only as the tape**, and only as a gross-error gate |
| **Clean plate / MTI** (temporal integration to sharpen inputs — RETIRED) | **Any temporal averaging under F1** | Differs in object: MTI took a temporal median of the **background image** to sharpen line inputs; averaging **pose measurements** across frames is a different estimator. Allowed, but the precedent is a warning — temporal integration has already failed once here to deliver the sharpening it promised |

One more, not in CLOSED.md but in "What has not worked": the **single-frame court auto-seed** row
(*"7 of 10 worse than starting from a blank rectangle; only multi-frame consensus separates the cases"*)
is the second measured argument against a strictly per-frame, stateless design. It does not forbid item
1; it should be quoted at F1.

---

## (c) Sequencing

Constraints that set the order: the phone port has never been started and nothing here has run on a
phone; the amateur keypoint model does not exist; the GPU runs **one job at a time**; and the floor is
SPEC §3 (5 cm p90, 10 cm kills — a measurement convention, not a founder bar).

**0. FIRST: the wrong-camera discriminator re-score.** ~1 session, backend-dev, **no new data and no new
model**. Take arm K's existing 400 trials and ask one question: does the final photometric cost separate
the 35 wrong cameras from the 365 right ones? **Three roadmap items depend on the answer** — item 3's
anchor selector, item 1 Tier 2's acceptance rule, and item 4's "not locked" trigger all assume a cost
that can tell a right camera from a wrong one. If it separates them, item 3 is nearly free. If it does
not, item 3 needs a different discriminator and we learn that for one session instead of six. Highest
leverage per session in the entire roadmap.

**1. In parallel (CPU, no GPU contention): the pyramid / iteration-budget experiment.** 1–2 sessions.
Does a coarse-to-fine schedule with a fraction of the iterations retain arm K's per-line p90? Same 400
seeds, one variable. **This is the gate on all Metal work.** Report wall-clock alongside precision.

**2. Item 2 — the amateur keypoint seed model. Start its data build now; it owns the GPU.** 4–8 sessions
and the longest lead time in the roadmap. **Items 1 Tier 1, 4's global re-localisation, and any court
found automatically at all are blocked on this.** Synthetic renders first (exact labels, leak-clean,
unlimited low mounts), real footage for availability validation only.

**3. Item 3 — multi-anchor fits plus the rewritten net-tape gate.** 2 sessions, CPU, **blocked on step
0** for its selector. Not blocked on item 2: the anchors are fixed height priors, not model output.

**4. Item 4a — multi-scale paint check, and score the existing dev-seed recovery under pre-registration.**
2 sessions, CPU, blocked on nothing. Note this partly answers open item **A** above: the "on-paint check
says not locked" trigger is the replacement for SPEC §1's 15 px / 3-frame drift rule, which was set for
a different mechanism.

**5. Item 1 Tier 2 — the Metal/Accelerate port.** 3–5 sessions. **Blocked on step 1 (does the algorithm
hold 5 cm cheaply) and on F3 (a device to measure).**

**6. Item 4b — global neural re-localisation.** Blocked on item 2.

**Not built at all: item 1 Tier 1 as a shipped camera.** See §e.

**Price, honestly: ~12–20 sessions before anything runs on a phone at target.** The cut line inside our
own scope is **shell**. SPEC §5 says a court result that only holds on hard courts is not a passing
result, and shell is our worst surface by a distance (CourtNet **0/80** frames, proposal recall 2 of 10
clips, 3 shell clips producing no lock at all). Every session spent on the Metal port is a session not
spent on shell. **That is the something-else each yes above is costing.**

---

## (d) The accuracy floor per item — I own these, and they are pre-registered here

| Item | PASS floor | KILL | Measured against |
|---|---|---|---|
| **1 Tier 1 (as SEED)** | Camera height error **p90 ≤ 0.15 m** and focal error **p90 ≤ 5%**; and after the paint fit, **wrong-camera rate ≤ 2%** over ≥400 trials | Height p90 > 0.35 m, **or** wrong-camera rate ≥ 8.75% (i.e. no improvement on arm K) | The exact rendering camera, on **held-out** synthetic scenes |
| **1 Tier 1 (as shipped camera)** | *No floor is offered. Not to be built* — see §e | — | — |
| **1 Tier 2 (fast fit)** | **Every line p90 ≤ 5 cm** and far baseline **≤ 5 cm**, no worse than arm K's 4.43 cm by more than the ~0.7 cm encoder noise; one variable changed, same seed; **wall-clock stated on a named device** | Any line > 10 cm, or far baseline > 5 cm | Exact projected court geometry, the CP1 arm P scene |
| **Per-frame, stateless precision** (only if F1 holds) | Every line **p90 ≤ 5 cm per frame** across a swaying sequence with **no temporal state** | > 10 cm p90 | The rendering camera. **Starting point: G3 measured p90 9.2–10.9 cm on good setups under steady sway — the mandate is currently missed by about 2x, and that is measured, not predicted** |
| **2 (amateur keypoints), availability — check this FIRST** | **≥ 8 of 14 keypoints above threshold on ≥ 90% of frames**, on ≥ 12 of the 16 strict-refs clips and ≥ 6 of 10 shell clips | Median < 4 keypoints on any surface (below the minimum for any homography) | Real footage, counted; no precise labels needed or used |
| **2 (amateur keypoints), quality** | As item 1 Tier 1's seed floor | As above | Synthetic truth. **Never** the gold pool's computed non-corner keypoints (hard rule 4; C2 is VOID) |
| **3 (multi-anchor)** | **Wrong-camera rate ≤ 2%** over 400 trials, with **no per-line p90 regression**; one variable, same seed | Wrong-camera rate ≥ 8.75%, or any line p90 worse than arm K | Arm K's existing rig and scene |
| **3 (selector precondition)** | The chosen cost separates wrong from right cameras at **≥ 90% sensitivity with ≤ 5% false invalidation** | Below that, the anchor selector is choosing blind and item 3 is redesigned, not tuned | The existing 35/365 split — **no new data required** |
| **3 (net-tape gate)** | Flags **≥ 80%** of the 35 known wrong cameras at **≤ 2%** false flags | **Any** false flag on a correct solution from a **1.3–2.2 m** mount | Arm K trials, plus low-mount cases specifically |
| **4 (multi-scale paint check)** | Detects a 14 px knock within **1 frame on ≥ 95%** of trials at **≤ 1%** false "not locked" during steady sway; and on a court displaced onto a **neighbouring line**, reports not-locked **≥ 95%** | **Any** configuration in which a wrong-paint lock reports `locked`. G3 measured that outcome at 7–10 m for 50 frames; it is worse than no answer | Rendered sequences against the rendering camera |
| **4 (recovery, either path)** | Every line back within 5 cm within **15 frames** on **≥ 95%** of knocks, **including a ~4x knock (~56 px)** | A knock class that never recovers | The rendering camera. Beat the dev-seed result, which loses a 4x knock permanently |

Two floors that apply to everything. **First, state in one sentence what each number was measured
against** (hard rule 1) — a photometric or reprojection residual is a diagnostic and certifies nothing
(hard rule 5). **Second, no item is "trusted" on a desktop timing** once a device number is obtainable;
until then every latency figure in this roadmap is explicitly a proxy.

---

## (e) What I would not build

1. **Tier 1 as the shipped camera.** Arm K0 measured this exact object at **6.65 m** on the far baseline.
   It is not a 20% miss to be tuned away, it is two orders of magnitude, and C1 explains why it is
   structural rather than a training problem. Build the model, type its output as a seed, and let the
   paint fit decide the camera.
2. **The Metal port before the desktop pyramid experiment.** Buying latency inside a language/hardware
   port is the most expensive possible way to learn that the cheap algorithm does not hold 5 cm.
   3–5 sessions at risk against a 1–2 session experiment that de-risks them.
3. **Anything that trades the 5 cm target for latency**, specifically: (i) **accepting a per-frame
   independent estimate at 9–11 cm p90 because it is fast** — that touches the 10 cm kill and it is the
   definition of confidently wrong; (ii) **terminating the fit on a downsampled pyramid level** — the far
   baseline's margin is ~1.4 cm and the codec already spends 2.65 cm, so the final measurement must be at
   native resolution; (iii) **skipping the paint fit on "easy" frames** — we have no measured way to tell
   an easy frame from a wrong lock, which is step 0's whole point.
4. **The net-clearance check as the roadmap words it.** "Overlap ⇒ invalid" rejects correct courts on
   1.36–1.74 m mounts, which is every amateur clip we own. Rewrite to "predicted overlap must match
   observed overlap at the fitted height", or do not build it.
5. **Any training or scoring against the gold pool's non-corner keypoints.** They are computed from four
   clicks. This would grade a homography against its own output and burn a one-way TEST pool.
6. **A separate YOLO/MobileNet net detector, for now.** The net tape already has a parameter-free
   geometric locator and a matched-filter row finder, and a second model costs a training slot on a
   single GPU that item 2 needs more. Revisit only if item 2's model cannot carry the net line as one of
   its own keypoints. *Judgement, confidence 0.65 — the weakest call in this document.*
7. **Handheld.** SPEC §4 puts it out of scope. Item 1's "knock" means fence sway and bumps on a fixed
   mount, and every measurement here assumes that. If the founder means handheld, everything above needs
   re-pricing.

---

## (f) Founder decisions this raises

> **ANSWERED 2026-09-18 — BOUNDED STATE.** The founder chose the middle option below, in their own
> framing: *"the court is found in the image every frame, but the camera may be refined across
> frames."* Binding reading: a saved court is **never propagated** and there is **no snap**; every
> frame measures the court in that image; the camera may be refined across frames (temporal
> averaging is allowed, and is the route under 5 cm); the independent on-paint check runs **every
> frame**, so a wrong court can never be reported as good. The G3 failure mode — a stale pose
> reported as `tracking` while 7–10 m out — is what the per-frame check exists to make impossible.
> **Consequence for the roadmap:** item 1's stateful fallback is permitted within these bounds;
> the stateless per-frame precision floor (p90 ≤ 5 cm with no state) is NOT the bar the tracker is
> held to. The accuracy floor itself is unchanged: every line p90 ≤ 5 cm, 10 cm kills.

**F1 — Does the no-state, no-snap per-frame mandate stand? This blocks the most work, and the roadmap
asks to suspend it in its own item 1.** Item 1's fallback is worded *"if the founder permits stateful
execution when direct tracking is valid"* — which contradicts the 2026-09-18 mandate prohibiting
temporal tracking dependencies. **I am surfacing the conflict, not resolving it.** The trade-off, with
the measurements attached:
- **With state:** the warm, seeded step is already **0.020 s** on desktop CPU, and **temporal averaging
  is the known route to getting under 5 cm** — G3 recorded that single-frame snaps sit at about 5 cm
  *median*, so the last factor of two comes from averaging. The risk is precisely what G3 measured: a
  stale pose reported as `tracking`, 7–10 m out for 50 frames.
- **Without state:** the cheapest measured cold path is **9.6 s**, and the best measured per-frame
  precision is **p90 9.2–10.9 cm** — above the 5 cm target and touching the 10 cm kill. The stateless
  mandate is not currently known to be reachable, and that is a measurement, not a doubt.
- **A middle option, if you want one:** bounded state — carry a pose for at most N frames, run an
  independent on-paint check *every* frame, and force a full re-fit the moment it fails. That keeps the
  cheap path while removing the exact failure mode G3 caught. It is still "state", so it is your call
  whether it counts.

**F2 — Mount height: require ≥ 2.0 m, or accept an inferred far baseline?** Below ~2.0–2.2 m the net tape
overlaps the far baseline and the information is not in the image. All four named amateur mounts we own
are 1.36–1.74 m. Either **(a)** the app requires a fence clamp at ≥ 2.0 m and says so at setup — costs us
users on tripods and standing mounts — or **(b)** below 2.2 m the far baseline is inferred from the near
court plus regulation dimensions, which is legal under capability 1 but whose precision **has never been
measured** and would need its own pre-registered experiment. Choosing (b) without measuring it means
shipping a number we cannot defend on the majority of real mounts.

**F3 — Do we unblock device access?** Nothing in this repo has run on a phone; the iOS latency harness
compiled green and sideloading is blocked (Sideloadly −22410), which STATE says not to reopen without
you. Every latency figure in this roadmap is a desktop proxy until it is unblocked. **The trade-off:
without one device number we cannot distinguish a 3x miss from a 100x miss**, and the whole of item 1 is
a latency claim. Do you want to fund an install route (paid developer account / TestFlight / other), or
do you accept that item 1 is designed against desktop proxies?

**F4 — Does item 2 own the GPU uncontested?** One RTX 5060 Ti, one job at a time. Item 2 is the only item
that needs it and it is the item that unblocks the other three. Confirm nothing queues ahead of it.

**F5 — Synthetic-first training for item 2?** Our renderer gives exact labels, no leak risk, and
unlimited low-mount scenes; real amateur footage gives realism but has no label precise enough to train
against and cannot be used for line-placement truth. **Trade-off:** synthetic is the fastest and the only
leak-clean path, but it carries a sim-to-real gap we would discover at the availability-validation step
rather than in a lab. My recommendation is yes, with the real-footage availability floor in §d as the
mandatory gate before any further investment. *Judgement, confidence 0.8.*

**Also note:** deciding item 4 partly resolves **open item A** above (SPEC §1's 15 px / 10 s / 6-of-8
numbers), since item 4's on-paint check is the mechanism that would replace the 15 px drift rule. No
separate decision is needed now — but A should not be answered independently of item 4.
