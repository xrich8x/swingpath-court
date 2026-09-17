# What would actually move court detection recall?

> **researcher, 2026-09-09.** COURT ONLY. No code, no measurement (no Bash by design), no
> edit to `docs/STATE.md`. Every number below is either cited from a file I read, arithmetic
> on a constant I read in the source, or explicitly labelled as my judgement.
> This run **resumed** a literature survey killed by a usage limit; the unreachable-source
> list at the end carries over from that run and is not re-derived.
>
> **Cross-agent note (I have no `SendMessage`; the lead relays):** §1.4 and §2 name
> **five unscaled pixel constants in the PER-FRAME proposal path**, not just `AGREE_PX` in
> the vote. If that reading is right it changes what pm's §D.5 is about. **backend-dev and
> qa should read §2 before anyone touches a court constant.** I am proposing no change.

---

## BOTTOM LINE

**(a) The ~30 px@640 self-spread is EXPECTED, but not for the reason the question offers.
It is not an inherent precision floor of Hough line-fitting — that floor is 6–20× smaller by
arithmetic. It is a MIXTURE, produced by a discrete argmax over competing court hypotheses,
in an objective that is ill-conditioned along the court's DEPTH/WIDTH direction. The number
is therefore not a precision measurement at all, and no vote threshold rescues it.**

**(b) Nothing published solves our regime.** Every method I could reach is trained,
tuned and measured on **broadcast** footage. The two with real transfer value are
**MonoTrack's bipartite line-partition + combinatorial layout match** (which attacks the
exact mechanism this project called "wrong in principle") and **M-LSD** (a line detector
that already runs at 48.6 FPS on an iPhone). Both attack **availability** of correspondences,
neither attacks the ~6.4 px precision ceiling, and neither has ever been measured on indoor
shell footage by anyone.

**And the thing most likely to actually move shell recall is not in the literature at all.**
It is in `backend/swingvision/courtfit.py`: the per-frame proposal path carries at least five
absolute pixel constants that the repo's own convention says must scale, and their combined
effect is monotone in resolution — which is the exact shape of the observed failure
(640-wide gold 12/20 → 1920 references 2/20 → 3840 shell 0/10 recordings locking). **I am
not recommending a change. I am recommending one cheap falsification (§4.1) before anyone
spends another session on court search or court literature.**

---

# PART (a) — Is 30 px@640 frame-to-frame self-spread expected or anomalous?

**Answer: expected, and diagnostic — but the word "spread" is doing damage.** It is being
read as a *precision* figure (one estimator, Gaussian noise, σ ≈ 30 px@640). I believe it is
a *mixture* figure (several distinct court hypotheses, each internally tight, alternating
between frames). Those two have opposite remedies, which is why this matters.

**Confidence: 0.72** that the mixture reading is correct and the precision-floor reading is
wrong. What would move it: §4.1, which needs no new measurement.

## a.1 — The precision-floor hypothesis dies on arithmetic

`_detect_lines` (`backend/swingvision/courtfit.py:66–95`) is the only place image geometry
enters as lines. Its quantisation, at **native** resolution:

| source | value in source | at 3840 wide | in px@640 |
|---|---|---|---|
| `cv2.HoughLinesP` θ bin | `np.pi/180` = **1.0°** | — | — |
| θ error levered along a ~1500 px sideline | `1500·tan(1°)` | 26 px | **4.4 px@640** |
| `cv2.HoughLinesP` ρ bin | **1 px** | 1 px | 0.17 px@640 |
| `cv2.distanceTransform(DIST_L2, 5)` mask error | ~2% of distance | sub-px | negligible |

**And 4.4 px@640 is the pessimistic bound, not the expectation.** Lines are merged in normal
form with **length-weighted averaging** (`courtfit.py:86–94`), so a merged line's angle is an
average over many segments; my judgement is an effective 0.2–0.4°, i.e. **~1–2 px@640**.

Two further constants that could have been suspects are **already scale-invariant** and are
therefore cleared: `tol = max(2.0, w*0.006)` (`:658`) is 3.84 px@640 at every resolution, and
the merge radius `max(6.0, w*0.012)` (`:89`) is 7.68 px@640 at every resolution.

**So classical line quantisation accounts for ~1–4 px@640 against an observed 30. It is off
by 7–30×. The "inherent precision floor of the approach" reading is refuted by arithmetic on
the shipped constants.** Confidence 0.88 — this is close to a code fact; it fails only if
`refine_homography_bounded` or `_tethered_dt_polish` injects a much larger, unmodelled term,
which I did not read.

## a.2 — The error is ANISOTROPIC, and noise is not

From `docs/evidence/camera-motion-vs-court-agreement.md` (qa, 2026-09-09; measured **fit vs
fit**, never against human clicks — it is self-consistency, not accuracy), on clips with
**≤0.3 px** of camera motion:

| clip | near-baseline width spread | far-baseline width spread |
|---|---:|---:|
| `hillsborough_p02` | **3.3%** | **93.9%** |
| `flexi_joy_p07` | 9.8% | 34.9% |
| `hillsborough_p08` | 14.5% | 23.0% |
| `flexi_joy_p01` | 5.7% | 22.4% |

**A quantisation floor is roughly isotropic in the image.** What is measured here is 4–28×
worse at the far end than the near end, on identical static pixels, along one axis: **depth**.
A structured, single-direction error of that magnitude is a **conditioning** signature, not a
noise signature. `hillsborough_p02` alone settles it: a far baseline whose image length nearly
**doubles** between two frames of a motionless tripod is not a 30 px jitter around one answer.
It is two different answers.

## a.3 — The mechanism: the objective loses its depth observable, by design

`_ori_detail` (`:137–174`) is evidence-based on purpose, and the design note is correct for
faded paint: *"a line with NO paint anywhere near it is UNMEASURABLE → excluded entirely"*
(`ev`, `EVID_MIN = 0.20`). But compose that with a finding already in Part A of pm's triage:

> **Below ~2.0–2.2 m the net TAPE physically covers the far baseline** — a property of the
> court, not the camera (`docs/evidence/setup-envelope-net-occludes-far-baseline.md`).
> All four measured mounts (1.64 / 1.74 / 1.38 / 1.36 m) sit below it.

**When the far baseline carries no separable evidence, it is excluded from the score — and
with it goes the only observable that pins how DEEP the court is.** The remaining evidence
(near baseline, service lines, sidelines near the camera) is nearly invariant under a
one-parameter family that trades court depth against camera standoff and focal length. The
score is then almost flat along that family, and the argmax picks whichever member a
particular frame's noise favours.

**This predicts exactly the observed signature:** near end pinned (3.3–14.5%), far end free
(22–94%), on static footage, and "13 of 18 clips disagree principally about WIDTH". I know of
no competing hypothesis that predicts the near/far asymmetry. **Confidence 0.70.**

Corroborating, from the record and not from me: `docs/evidence/least-squares-court-fit.md`
notes that projecting world endpoints "explodes on low mounts (**204 px** under the *human*
homography on `hillsborough_p02`, far baseline at the vanishing line)". The far baseline on
that clip is essentially at the horizon. **It is not merely poorly observed there — it is
nearly unobservable, under the human's own calibration.**

## a.4 — And the estimator is a discrete argmax, so its output is a MIXTURE

`autodetect` (`:646–764`) is not a continuous estimator with a noise distribution. It:

1. scans a fixed **4×4×4×4×4 = 1024**-point coarse grid (`COARSE_GRID`, `:770`), adds prior
   and low-cam seeds, sorts;
2. refines a local grid around the **top 3**;
3. refines **at most `topk = 12`** of the resulting seeds;
4. keeps `best` = **argmax of `rankv`** among those that pass the accept gate.

A player crossing a sideline, or one Hough segment fragmenting, changes `g` and `st` by a
little — and that can change **which hypothesis is argmax**. The output then jumps
discontinuously between distinct courts. **The per-clip set of 8 fits is a sample from a
mixture over hypotheses, not a scatter around a mean.** Reporting its median pairwise
distance as a "self-spread" describes the mixture's separation, not any estimator's precision.

**This is the "the search never found it" vs "it found it and lost the vote" distinction, and
it is being collapsed.** `AGREE_PX` refusing to merge two genuinely different courts is the
vote **working**, not failing.

## a.5 — The reconciliation the record needs (and this is for the lead)

`docs/STATE.md` currently carries **both** of these:

- *"Court proposal recall is 8/20 = 40%: **THE SEARCH BINDS**, not the vote"* (2026-09-09).
- *"**Widen the seed grid** — reaches courts the old grid could not and **gets every one of
  them wrong** (26 px, 78 px)"*, and *"Raising `topk` 12 → 40 → 150 — **no clip moves**,
  7× compute"*, and reachability's **stopping rule** (nearest seed already in reach on 31/38).

Read as "the enumeration is too small", these contradict. **They are consistent under one
reading only: the enumeration is adequate, and the OBJECTIVE's argmax is not the true court.**
Widening reached the truth and the score preferred something else; raising `topk` fed the
score more candidates and it chose the same ones. "Search binds" is true of the *ranked-argmax
pipeline as a whole*; it is **not** true of the seed enumeration, and the difference decides
what to do next. I would ask the lead to phrase the STATE row as **"the proposal STAGE binds"**
rather than "the search binds", because three people have already read it the other way.

**Confidence 0.80.** Disproved if the modality test (§4.1) comes back unimodal.

---

# PART (b) — What in the literature works on OUR regime

**Blunt summary: nothing was measured on our regime by anybody.** Everything below was
trained and evaluated on broadcast soccer, broadcast tennis, or broadcast badminton. The
honest statement for each is "what footage this number came from", and in every case it is
not ours. **No published paper I could reach reports a number on indoor, low-mount,
truss-and-mesh amateur court footage.** That absence is itself the most important finding of
Part (b).

Ranked by expected value **for us**.

### 1. MonoTrack's court module — bipartite line partition + combinatorial layout match

**What it is.** Hsu et al., *MonoTrack: Shuttle trajectory reconstruction from monocular
badminton video*, CVPRW 2022 (arXiv 2204.01899, code at `github.com/jhwang7628/monotrack`).
Explicitly a Farin improvement: colour threshold → Hough → **partition lines into the two
pencils by maximum-weight bipartite subgraph instead of hard-coded angle constraints** →
combinatorial search over court-layout assignments.

**Why it ranks first.** It is the only published method I found whose *contribution* is at
the stage that binds for us, and it attacks a mechanism this project has already named:

> *"Building the court quad from the DETECTED LINES — **wrong in principle, not mis-tuned**.
> Under perspective the two doubles sidelines converge, so they form no angular cluster."*
> (`.claude/agent-memory/researcher/court-detection-negatives.md`)

MonoTrack's whole point is that angular clustering is the wrong grouping operator and a graph
partition is the right one. **Reported: 73.9% → 85.5% success at IoU > 0.8, average IoU 0.97,
40× faster than the original.** Measured on 26 TrackNetV2 **broadcast** badminton matches plus
**40 YouTube matches "with varied camera angles outside the broadcast view"** — the closest
thing to our regime in the literature, and still not indoor-shell tennis from a fence clamp.

**Rule-3 check — and this is the one that needs care.** It sits adjacent to **two** measured
negatives: "building the court quad from detected lines" (best constructed quad 68–256 px from
truth) and the whole **joint line-to-model correspondence** branch, killed 2026-08-29/09-04
(`court-correspondence-gate.md`, `least-squares-court-fit.md`: C3 reconstructs **17.1 px@640
given the TRUE correspondence**, against a shipped 8.1). **I am not proposing it as a fix, and
if it were built it would inherit the 17.1 px ceiling** — it changes *how often* a
correspondence is found, not *how good the fit is once found*. Its honest best case is
converting "produced nothing" into "produced something at ~17 px", which is inside the 20 px
wrong-court line but outside the 8.1 px bar. **Under pm's §D.7 that is a seventh branch and
the answer is no.** I record it because it is the only published idea that would be *new*
here, not because it should be funded.

**iOS / A13 / on-device:** trivially fine — pure CPU combinatorics, one-off on 8 frames, no
ANE, no network. **Training data: none for the court module** (it is classical); the paper's
labels were for evaluation. **Proposal stage: yes, that is precisely where it acts.**

### 2. M-LSD — a learned line detector that already runs on an iPhone

Gu et al., *Towards Light-weight and Real-time Line Segment Detection*, **AAAI 2022 oral**
(arXiv 2106.00186, `github.com/navervision/mlsd`). M-LSD-tiny is **2.5% of TP-LSD-Lite's model
size** and the paper reports **48.6 FPS on iPhone** (their measurement, their device, not ours).

**Why it could matter for shell.** Our shell failure is plausibly an **evidence-availability**
failure, not a fitting failure: `_clay_mask` reconstructs the mask by re-rasterising Hough
segments, so anything Hough misses does not exist downstream. A learned LSD finds low-contrast
and fragmented lines that a ridge-mask + Hough pass does not.

**Why I still rank it second and would not fund it today.** It will also find **trusses,
ceiling-light rails, fence rails and the top of the net** — with *more* recall than Hough. Our
problem in an indoor shell is not only "too few lines", it is "too many confident wrong lines".
Adding a better line detector without a better line **discriminator** is as likely to hurt as
help, and the project's own VP-filtering closure explains why the obvious discriminator does
not exist: *"a shared VP proves 3D parallelism, not coplanarity; a building aligned with the
court is indistinguishable by line direction alone."*

**Rule-3 check:** not in "What has not worked". The nearest rows are the mask-replacement
family (CLAHE / Lab chroma, rejected on the product gate) and clean-plate/MTI (retired
2026-09-06). A learned LSD is a different object from both — it replaces the *detector*, not
the *mask preprocessing*. **Not a re-proposal**, but it lands in a family with two closures.

**iOS / A13:** the strongest of any learned option here. MobileNetV2-family backbone, conv /
ReLU / BN / upsample only — the same operator set `docs/STATE.md` already certifies as
zero-risk ANE for CourtNet. One-off on 8 frames, so thermal exposure ~nil. Export path is
TF → coremltools (the repo's existing exports are PyTorch → Core ML, so this is a different
toolchain and a real, if small, integration cost). **Training data: NONE — use the released
wireframe-pretrained checkpoint as-is.** That is unusual and is why it ranks this high.
**Proposal stage: yes**, it replaces `_detect_lines`' input.

### 3. Homayounfar et al., *Sports Field Localization via Deep Structured Models*, CVPR 2017

Branch-and-bound inference in an MRF over the **space of all parametrised fields**, with
generalised integral images giving cheap bounds — i.e. a **provably optimal global search**
over the pose space, on top of a 6-class semantic segmentation (vertical lines, horizontal
lines, circles, grass, crowd). Soccer and ice hockey, **broadcast**.

**Its value to us is diagnostic, not prescriptive.** It is the published answer to "did the
search miss it, or did the score prefer something else?", because branch-and-bound returns the
**global** optimum of the score. **But we already have that answer from our own negatives**
(§a.5): widening the grid reached the truth and the score rejected it. **Rule-3: proposing
branch-and-bound as a fix would be a re-proposal of "widen the seed grid" and "raise `topk`"
in a more expensive wrapper. Do not.** Its segmentation front-end also needs exactly the
labels we do not have.

**iOS:** the segmentation net is fine; branch-and-bound over 5–7 DOF on an A13 CPU is a real
cost but one-off. **Training data: pixel-level line/surface segmentation on indoor shell
courts — we have none, and this is the most expensive data ask on this list.**

### 4. TVCalib (WACV 2023) and the SoccerNet calibration line — *No Bells, Just Whistles*
(CVPRW 2024), PnLCalib (2024)

TVCalib (Theiner & Ewerth, arXiv 2207.11709) is the methodologically closest to what this
project actually wants: **calibrate a camera from segment correspondences via a differentiable
objective, rather than estimate a homography from 4 points** — which is the same move as this
repo's own `_cam_refine` / `cam_fit_quad` hard camera gate. *No Bells, Just Whistles*
(arXiv 2404.08401) generates keypoints from SoccerNet annotations plus line-intersection
augmentation and then does plain DLT.

**Assessment: correct direction, wrong data, and the direction is already taken here.** The
repo already refuses any quad no physical camera can produce (`courtfit.py:752–757`). What
these buy over ours is a **learned, dataset-scale front end** — and both front ends are trained
on SoccerNet broadcast. Our own CourtNet experiment is the measured instance of exactly this
transfer failing: **2–3 of 14 keypoints clear threshold on amateur frames, gold 12/20 → 2/20,
shell 20/80 frames → 0/80** (`docs/evidence/cnn-global-classical-local.md`).

**Rule-3 check: this is the closest thing on my list to a re-proposal, and I am flagging it as
one.** "Improving CourtNet for auto-calibration" and "CNN-global → classical-local" are both
measured negatives here. A different broadcast-trained keypoint network is the same experiment
with a different checkpoint. **Do not fund.** **Training data: SoccerNet-scale annotation of
our own regime.**

### 5. Synthetic data + domain randomisation (SoccerSynth-Field, arXiv 2503.13969; SOLD2)

The published answer to "we have no labels in the target domain": render the known court
geometry under randomised camera pose, lighting, surface colour, occluders and clutter, and
pre-train on that. **Directly relevant, because our binding constraint for every learned
option above is that we have zero indoor-shell ground truth**, and this project already owns
a renderer of the right kind (`tools/synth_truth.py`).

**Why it is ranked fifth and not first:** it produces *training data*, not a *method*, so it
only pays if one of items 1–4 is worth training — and items 3 and 4 are barred by rule 3.
Also, the thing we would most need to randomise is precisely the thing hardest to synthesise
convincingly: **indoor structural clutter** (trusses, ceiling-light rails, mesh, adjacent
courts). A domain-randomised model that has never seen a real roof truss is not obviously
better than one trained on broadcast. **Rule-3: not in the table.**

### 6. Padel / pickleball work — surveyed, and there is nothing to take

The padel and pickleball literature (IDEAL 2024 padel tracking; the ResNet50-keypoint
pickleball systems) is the right *regime* — enclosed courts, mesh, glass, amateur cameras —
but it is engineering write-ups, not measurement: **"no public academic datasets currently
exist for pickleball and padel"**, and the court stages are ResNet50 keypoint regressors
trained on the authors' own unpublished data with no reported court accuracy I could find.
**Nothing citable, nothing transferable.** Recorded so the next run does not re-survey it.

### And the one already ruled out before this run

**arXiv 2404.06977, "Accurate Tennis Court Line Detection on Amateur Recorded Matches"**
(Agrawal / Sundararajan / Sagar, IVPAI 2024). Full text unreachable (§5). From abstract and
indexed text: **enhanced Hough + homography** — the Farin-family joint fit **this project
built and killed**. Its three additions (MTMT shadow removal, object-detector player removal,
court-colour filtering) all attack **outdoor** degradations. **None attacks indoor structural
clutter.** Claimed "94% accuracy in the best case", metric undefined. **Rule-3: its core is
already a measured negative here.** Do not chase it further.

---

# PART 2 — The thing that is not in the literature: five unscaled constants in the PROPOSAL path

This is where I would put the next session, and it costs nothing to check.

## 2.1 The pattern nobody has named

Accept rate falls **monotonically with capture resolution**, across three different pools:

| pool | frame width | outcome | source |
|---|---:|---|---|
| gold | **640** | **12/20** accepted | `court-mask-sweep-item-is-already-shipped.md` |
| references | **1920** | **2/20** accepted | `camera-motion-vs-court-agreement.md` control #4 |
| shell | **3840** | 3 recordings lock **0 of 8 frames**; 1 of 5 recordings reaches | `candidate-proposal-recall.md` |

`AGREE_PX` is the standing explanation, and it is real (30 / 10.0 / 5.0 px@640 at 640 / 1920 /
3840). **But `AGREE_PX` cannot explain the zero-lock clips.** A "lock" is a **per-frame**
result from `auto_fit_frame` → `autodetect`; `AGREE_PX` is read **only** by `consensus`
(`courtfit.py:774, 789`), which runs *after* locking. **A clip that locks 0 of 8 frames was
refused by the per-frame proposal path, where `AGREE_PX` is not consulted at all.**
Confidence 0.85 — I read `consensus` and `autodetect` in full; I did **not** read
`auto_fit_frame`'s body, and one grep would settle it.

## 2.2 So what IS resolution-dependent in the per-frame path

Read from source. CLAUDE.md's convention is *"every pixel threshold scales by
`frame_height/720` — except `static_radius_px`"*. These do not:

| # | constant | where | at 3840 vs at 640 |
|---|---|---|---|
| 1 | **`cv2.Sobel(..., ksize=3)`** for the orientation map | `courtfit.py:127–129` | a **3×3** operator on paint that is ~2 px wide at 640 and ~12 px wide at 3840 |
| 2 | `HoughLinesP(threshold=45)` — an absolute accumulator count | `:73` | a real line contributes ~6× more pixels ⇒ **~6× easier**, admits more spurious lines |
| 3 | `HoughLinesP(maxLineGap=12)` (and `14` in `_clay_mask`) | `:74`, `:111` | 2.0 px@640 at 3840 vs 12 px@640 at 640 ⇒ **6× stricter**, fragments occluded lines |
| 4 | **`cv2.line(clean, ..., 255, thickness=2)`** — the clay/shell mask is a *re-rasterisation* | `:115` | a **2-px hairline** redrawn over paint that is ~12 px wide |
| 5 | `snap_court(max_move_px=30.0)` | `:918` | 5.0 px@640 at 3840 vs 30 px@640 at 640 |

**Constant #1 is the one I would test first, and it has a clean mechanism.** `_ori_detail`
requires `align >= athr = 0.80`, where `align` is the double-angle agreement between the
projected court line's direction and the **local image gradient direction** at that pixel.
A 3×3 Sobel taken **in the interior of a 12-px-wide painted line** sees no gradient — the
paint is flat there — so `arctan2(gy, gx)` returns the direction of sensor/compression noise.
`align` becomes random, `sup` fails, the per-frame agreement `g` collapses, and the
`g >= accept (0.33)` gate refuses. **At 640 the paint is 2–3 px wide, every pixel on it is
adjacent to an edge, and the same operator works perfectly.** This predicts refusal that gets
worse with resolution and is worst on wide, well-painted indoor lines — which is shell.

**Constant #4 compounds it on exactly the shell path.** Shell reaches `_clay_mask` via the
`_fallback` retry (`:758–763`). `_clay_mask` **discards the image evidence and replaces it
with straight 2-px lines drawn between Hough segment endpoints**. At 3840, a 1° endpoint-angle
error over a 1500 px segment displaces that hairline by ~26 px — with a 2-px hairline and
12-px-wide true paint, the reconstruction can **miss the paint entirely and leave no overlap**.
At 640 the same angular error displaces a 300 px segment by ~5 px and the 2-px hairline still
partially covers 2–3 px paint. Then `_precompute` runs `_detect_lines` **again** on that
hairline mask — a second Hough on a synthetic reconstruction of the first.

**Rule-3 check, stated explicitly.** I read `docs/STATE.md` "What has not worked" lines
138–206 and the ~20 court rows in my own memory file. **None of these five constants appears
anywhere in that table.** The nearest rows are: *"Widening / height-scaling `AGREE_PX`"*
(a **vote-stage** constant, and pm has ruled on it — different stage, different constant);
*"Raising the detector's input resolution"* (that row is **ball**, not court);
*"Crop-and-upscale"* (rejected — it **up**scales the input, the opposite direction);
*"Global mask replacement — CLAHE / chroma"* (a different mask, not a scaling defect);
*"Clean plate / MTI"* (temporal integration, retired). **This is not a re-proposal.** It is
also not, on its own, a proposal — see §4.

## 2.3 The product tension this exposes, for pm

`courtfit.py:960–986` ships user advice that **"RESOLUTION is the dominant free lever"** and
tells the user to record at 4K, on measured geometry (reliable span 17% at 720p → 48% at 4K
from a 1.5 m mount). **That advice is correct for measurement precision and may be actively
harmful to auto-detection**, because the auto-detector's accept rate falls with resolution.
The two are not in conflict on the shipped product — v1 uses **manual** 4-tap calibration, and
manual calibration only gains from 4K. **But if auto-detection ever reopens, the setup advice
and the detector pull in opposite directions, and nobody has written that down.** Decision left
open; I am not proposing a change to the advice.

---

# PART 3 — Engaging with pm's cut line, not routing around it

`docs/evidence/court-triage-2026-09-09.md` §D.7. I agree with four of five and want to sharpen
the fifth.

| pm's line | my position |
|---|---|
| **No seventh auto-detection branch** | **Agree.** MonoTrack (item 1) is the only candidate that would be one, and I have marked it as not-to-fund for exactly this reason. |
| **No multi-homography** | **Agree, and the product argument is right** — a propped phone records one continuous take. Nothing in my analysis touches it. |
| **Do not ship the `AGREE_PX` normalisation** | **Agree**, and §2.1 strengthens the case *against* it for a new reason: `AGREE_PX` **cannot** be the cause of the zero-lock shell clips, because it is not read on the per-frame path. Normalising it would be treating a stage that is not failing. |
| **Do not touch `courtnet_ft.pt`** | **Agree.** 17 of 20 gold clips in its training pool; it is a mirror. |
| **The court-normalised agreement metric is the right experiment, parked unfunded** | **Half-agree, and this is my one substantive disagreement.** pm identified the right *property* (normalise in court terms, weight width separately) but attached it to the **vote**. §a.3 says the width degeneracy originates in the **per-frame objective**, where the far baseline is dropped as unmeasurable. A court-normalised metric at the vote stage measures the disagreement more fairly; it does not remove it. **If it is ever funded, fund it at the score, not at the vote.** Still unfunded either way — I am not asking for it. |

**One thing I would add to the cut line.** pm ranks the **direct-line-click falsifier** last on
the grounds that its best case changes no v1 decision. **That reasoning is right and it applies
with more force to everything in Part (b).** Every literature item above, at its best, converts
a closed subsystem from "wrong" to "less wrong". §4.1 is the only item in this document whose
cost is near zero, and it is the only one I am asking for.

---

# PART 4 — The one pre-registered test, and the one I am NOT asking for

## 4.1 THE CHEAP ONE — modality, from an artefact that already exists

**Question:** are a clip's 8 per-frame fits a *scatter* around one answer (precision floor) or
a *mixture* of distinct answers (mode switching)?

**No new measurement is required.** `scratchpad/interframe_agreement.py` → `interframe.json`
(named in `camera-motion-vs-court-agreement.md` §"RAW DATA") already stores **all pairwise
distances per clip**. This is re-reading a computed artefact.

**Pre-registered, before anyone looks:**

- **Metric:** for each clip with ≥3 locked frames, single-linkage cluster the per-frame quads
  at a 12 px@640 threshold; report cluster count, within-cluster median pairwise distance, and
  between-cluster median.
- **MIXTURE** if, on **≥6 of the ~12** measurable clips: ≥2 clusters, within-cluster median
  **≤ 8 px@640**, between-cluster median **≥ 25 px@640**.
- **PRECISION FLOOR** if, on **≥6 of ~12**: exactly 1 cluster at that threshold, or
  within-cluster median **≥ 15 px@640**.
- **INDETERMINATE** otherwise — and it stays indeterminate; the bands do not move after the
  fact.
- **Kill condition:** if it returns PRECISION FLOOR, **my part (a) is wrong**, the classical
  line-fit path has a genuine ceiling at this resolution, and every item in Part (b) that acts
  on the proposal stage is dead with it. Say so and close it.
- **What it is measured against:** nothing external. It is a **shape-of-distribution** question
  about fits, not an accuracy question. **It cannot and must not be reported as accuracy** —
  the same caveat qa attached to `D_raw`.
- **Cost:** minutes, no footage decode, no gold, no human.
- **Who:** qa (Bash). **It must not "fix" anything it finds.**

**Why this is the cheapest thing to falsify in the whole document:** it decides between two
readings of a number that four documents now quote, it needs no new data, and its negative
outcome closes a research direction rather than opening one.

## 4.2 The one I am NOT asking for, and why I am naming it anyway

The obvious follow-on to §2.2 is: *compute the orientation map on a resolution-normalised
gray image (or scale `ksize`), keep one variable, re-run the gate.* **I am not proposing it.**
Three reasons: court auto-detection is closed for v1; it would be a change to shipped
perception code in a maintenance lane; and pm's §D.7 rightly says an accuracy win in a feature
we are not shipping loses to anything at all in a feature we are.

**But it should be RECORDED, because it is the first mechanism anyone has offered for the
zero-lock shell clips that is not `AGREE_PX`, and `AGREE_PX` provably cannot be it.** If court
auto-detection ever reopens, this is where I would start, ahead of every paper in Part (b).
Exact text I would want in `docs/STATE.md` "Open" (**for the lead to place or discard — I have
not touched STATE**):

> **The per-frame court proposal path carries five unscaled pixel constants, and `AGREE_PX`
> cannot explain the zero-lock shell clips** — assessed 2026-09-09, not measured.
> `AGREE_PX` is read only by `consensus`, never by `auto_fit_frame`/`autodetect`, so the three
> shell clips that lock **0 of 8 frames** were refused by the per-frame path where it does not
> apply. Five constants there violate CLAUDE.md's `frame_height/720` convention:
> `Sobel(ksize=3)` for the orientation map (`courtfit.py:127`), `HoughLinesP(threshold=45)`
> (`:73`, ~6× easier at 4K), `maxLineGap=12`/`14` (`:74`, `:111`, ~6× stricter at 4K),
> `cv2.line(..., thickness=2)` in `_clay_mask` (`:115` — the shell path **re-rasterises** its
> own evidence as 2-px hairlines), and `snap_court(max_move_px=30.0)` (`:918`). Accept rate
> falls monotonically with capture resolution (640 gold 12/20 → 1920 refs 2/20 → 3840 shell
> 0/8 on three clips). **Mechanism offered, not measured; no change proposed; court
> auto-detection remains closed for v1.** `docs/evidence/court-recall-what-would-actually-move-it.md`

---

# PART 5 — What I could NOT reach

So the next run does not repeat it.

**arXiv 2404.06977 full text — UNREACHABLE, 10 routes, do not retry these:** arXiv has no
HTML/ar5iv version (404, or 307 back to `/abs`); the PDF downloads but cannot be rendered
locally (no poppler); `r.jina.ai` **403**; `academia.edu` **403**; `aimodels.fyi` **403**;
`themoonlight.io` **429** (×3); Semantic Scholar API **429**; `papers.cool` returns metadata
only. Everything this project knows about that paper comes from the arXiv abstract plus
search-engine-indexed PDF text.

**Not attempted this run, by instruction:** the HuggingFace datasets
(`Gholamreza/tennis_court_keypoints_dataset` = a re-upload of yastrebksv's own 8,841-image
training set; CourtSide = axis-aligned boxes) — already surveyed and closed
(`docs/evidence/external-research-reconciled.md`).

**Reached but only at abstract/summary depth** — I did not open the full PDFs, so treat these
as second-hand: TVCalib (2207.11709), *No Bells Just Whistles* (2404.08401), Homayounfar CVPR
2017, SoccerSynth-Field (2503.13969), SOLD2 (2104.03362). **MonoTrack (2204.01899) I did reach
in full via ar5iv** and its court-detection numbers above are from the paper itself.

**Not read, and it is a real gap:** MonoTrack's actual court code (`github.com/jhwang7628/monotrack`).
The bipartite-partition claim is from the paper's prose, not from the implementation.

**Code I did not read, where a claim depends on it:** `auto_fit_frame`'s body (§2.1 confidence
0.85 rather than 0.95), `calibration.refine_homography_bounded`, `_tethered_dt_polish`,
`calibration.line_ridge_mask` and `court_line_mask`. If any of those carries a large
unmodelled term, §a.1's arithmetic bound is incomplete.

---

# Open questions

1. **Is the 8-fit distribution multimodal?** §4.1. Everything in Part (a) turns on it, and the
   data already exists.
2. **Does `court_line_mask` thin/skeletonise?** If it returns a **1-px skeleton** at every
   resolution, my constant-#1 argument weakens sharply — the samples would land on a thin ridge
   where a 3×3 Sobel still works. I could not establish this without reading `calibration.py`.
   **This is the single cheapest way to falsify §2.2**, and it should be checked before that
   section is quoted.
3. **Is there any indoor-shell tennis court dataset anywhere?** I found none. If the answer
   stays no, then every learned option in Part (b) carries an unfunded data line item, and that
   should be stated as a standing fact rather than re-discovered per proposal.
4. **Does the far baseline's exclusion (§a.3) actually fire on shell?** `_ori_detail` returns
   `n_ev`; nobody has reported its per-line breakdown. One instrumented run would confirm or
   kill the depth-degeneracy mechanism directly — but it is a measurement, and court is closed.
5. **`e8T34KoJzOw_s2`** — pm's open question 2, unchanged by anything here.
