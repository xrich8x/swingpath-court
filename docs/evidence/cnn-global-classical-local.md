# CNN-global -> classical-local: the court ordering flip

> A/B of the court **global-proposal stage** only. Built and measured 2026-09-09 by
> **backend-dev**. Scored against human-clicked corners. The shipped default is
> **UNCHANGED** — the flip is behind a flag and it **FAILED its pre-registered bar**.

## The claim under test

The founder's external research document argues our shell-court failures are a
**global search** failure — trusses, ceiling lights and mesh fencing outnumber the 8
court lines in the Hough output — and that the ordering should be inverted:
`yastrebksv/TennisCourtDetector` runs **CNN-global -> classical-local**, we run
**classical-global -> CNN fallback**. Its evidence is the upstream ablation on their
own val split at 7 px: base 0.936 / 2.83 px median; **+local refinement** 0.939 /
**2.23**; **+homography** **0.961** / 2.27; both 0.963 / 1.83.

**The premise is supported. The proposed remedy is not available to us.** Those are
separate findings and this file keeps them separate.

## Verdict

| | |
|---|---|
| **Premise** (global search binds) | **SUPPORTED** — qa measured proposal recall **8/20 = 40%**, below its pre-registered 60% "search binds" line, worst on shell. Quoted verbatim below. |
| **Remedy** (CourtNet as the global proposer) | **FAILS the pre-registered bar.** Gold **12/20 -> 2/20** accepted. On the reference clips **2/20 -> 0/20**, and **3 of 160 frames locked vs 89**. |
| **Mechanism** | Not the gate and not the vote. On the failing clips **CourtNet emits no proposal at all**: 2-3 of 14 keypoint heatmaps clear 0.40, and 4 are needed for a homography. |
| **Shipped default** | unchanged (`proposer="classical"`). Flag retained because the *local* half of the document's claim reproduced (below) and a differently-trained CourtNet is the live follow-up. |

## What was built

`backend/swingvision/courtfit.py`

```
auto_fit_frame(frame, calibration, court, *, with_score=False, proposer=None, weights=None)
fit_video_frames(frames, calibration, court, *, proposer=None, weights=None)
resolved_proposer(proposer=None)          # argument > COURT_PROPOSER env > "classical"
resolved_courtnet_weights(requested=None) # mirrors detect_court_learned's own order
```

The recipe is three stages — **GLOBAL localisation -> LOCAL refinement -> 6-DOF
lock** — and the flag switches **stage one only**:

- `"classical"` (shipped): `autodetect`, Hough lines + regulation-structure matching.
- `"courtnet"`: `calibration.detect_court_learned`, the vendored 15-channel heatmap
  net, used for global localisation; we take only the four doubles corners its
  homography implies.

Stages two and three — `snap_to_lines(min_coverage=0.0, max_move_px=60.0)` then
`lock_quad` — and `consensus` are the **same objects** for both arms. That is what
makes this one variable.

`verify=False` is passed to the CNN on purpose: `verify_court` is a second *accept*
test with no counterpart on the classical arm, and the brief says the shipped gate
and vote decide. Leaving it on would have made the A/B two variables.

**Tests:** `backend/tests/test_court_proposer.py` (7). The refactor-changed-nothing
proof is `test_default_matches_explicit_classical`; the courtnet arm is proved to run
*through* the shipped snap and lock by a stub detector, so the test needs no torch, no
weights and no clip. With the pre-existing `test_auto_fit_with_score.py`: **9 pass**.

**Harnesses:** `eval/proposer_ab.py` (both arms on the SAME decoded frames, `run_refs`
metric), `eval/proposer_rejects.py` (per-frame stage-of-death), and `--proposer` on
`eval/run_eval.py` (set through the environment so the shipped fit call site stays
byte-identical).

## Provenance

| | |
|---|---|
| Weights, arm B | `backend/weights/court_detector.pt` — the **upstream released checkpoint** (Jun 2023) |
| Why not the fine-tune | `detect_court_learned` **silently prefers `courtnet_ft.pt`** if it sits beside the requested file. That is our fine-tune and **17 of the 20 gold clips were in its training pool**; scoring it here would be self-grading. Both harnesses force the upstream file through `COURTNET_WEIGHTS` and print the **resolved** path, and `resolved_courtnet_weights()` exists so a stamp can never record the request instead of the resolution. |
| Commit | `3bf1734` (working tree, this change uncommitted) |
| Frames | K=8 per clip, `run_refs.frames_from` / `run_eval.load_gold`, identical indices across arms |
| Accept rule | `tag=="vote"` and `votes>=6` of 8 — `pipeline.calibrate_video` Tier 1, unchanged |
| Reference | human clicks only (`_exact` calibrations; `eala_pts_auto` excluded by rule) |
| Determinism | deterministic apart from `cv2.findHomography`'s unseeded RANSAC inside the vendored seam — noted, not changed |

## Pre-registered bar (written before either arm ran)

- **FLIP WINS** if B accepts more clips than A **and** B accepts zero court beyond
  20 px@640.
- **FLIP LOSES** if B accepts fewer, **or** accepts any court beyond 20 px@640 (a
  wrong court accepted is worse than a refusal — it is the failure the vote exists
  to stop).
- The **ordering hypothesis is SUPPORTED** only if B accepts >=3 clips A refuses and
  at least half of those gains are shell.
- Splits need n>=4 per arm or they are reported **UNDERPOWERED**.

Result: **FLIP LOSES**, on both populations, by the first clause. A failed bar stays
failed.

## Result 1 — the gold set (the founder's named gate: >=12 of 20, zero beyond 20 px)

`eval/run_eval.py --gold --all --k 8`, ~315 human-clicked frames, 640x360 cached.

| Arm | ACCEPTED | median consensus err | range | WRONG (>20 px) |
|---|---|---|---|---|
| A classical (shipped) | **12/20** | 8.1 px | 1.7-13.9 | **0** |
| B CourtNet-global | **2/20** | 4.1 px | 2.5-5.6 | **0** |

Arm A reproduces the documented shipped number exactly (12/20, median 8.1, 0 wrong),
so the harness is not the story. **Arm B fails the gate by 10 clips.**

B's lower median is a **selection effect, not a precision win** — it is the median of
the only two clips it accepted, both of which A also accepted. Per the brief, no
precision claim is made from it (see *Two things this cannot fix*).

Arm B locks 0 of 8 frames on **11 of 20** gold clips.

## Result 2 — the reference clips, split by surface

`eval/proposer_ab.py`, 20 human-calibrated clips at native resolution, both arms on
the same decoded frames. Documented shipped baseline for this population is 2/20 with
shell 0/10; arm A reproduces it.

| Surface | n | A accepted | B accepted | A frames locked | B frames locked |
|---|---|---|---|---|---|
| **Shell** (all 3840x2160) | 10 | 0 | **0** | 20/80 | **0/80** |
| **Hardcourt** (all 1920x1080) | 8 | 1 | **0** | 53/64 | **3/64** |
| **Clay** (1920x1080) | 2 | 1 | **0** | 16/16 | **0/16** |
| **All** | 20 | **2** | **0** | **89/160** | **3/160** |

Zero wrong-accepted courts in either arm — the one record neither arm spent.

Per clip (`e640` = mean projected-doubles-corner distance to the human court, scaled
to 640 px; `None` = no court produced at all; `stack` = the shared clay/shell rescue,
which is **not** a proposer and is identical machinery in both arms):

| clip | surface | res | mount m | A lock/votes/acc/e640 | B lock/votes/acc/e640 |
|---|---|---|---|---|---|
| A7vXlWIlyrI | Hardcourt | 1920 | 1.69 | 4 / 1 / no / 23.2 | 0 / 0 / no / 23.2 |
| am_hard_utr | Hardcourt | 1920 | 1.74 | 8 / 7 / **YES** / 13.23 | 0 / 0 / no / 25.84 |
| CYqapSq5llo | Clay | 1920 | 1.98 | 8 / 2 / no / 15.06 | 0 / 0 / no / 9.38 |
| e8T34KoJzOw_s2 | Hardcourt | 1920 | 1.76 | 8 / 2 / no / 9.42 | 0 / 0 / no / 19.06 |
| flexi_franz_p01 | Shell | 3840 | 2.50 | 3 / 1 / no / - | 0 / 0 / no / - |
| flexi_franz_p07 | Shell | 3840 | 2.51 | 3 / 1 / no / 73.79 | 0 / 0 / no / 73.79 |
| flexi_joy_p01 | Shell | 3840 | 1.36 | 2 / 1 / no / - | 0 / 0 / no / - |
| flexi_joy_p07 | Shell | 3840 | 1.36 | 5 / 1 / no / 75.01 | 0 / 0 / no / 75.01 |
| hillsborough_p02 | Shell | 3840 | 1.64 | 3 / 1 / no / 93.98 | 0 / 0 / no / 93.98 |
| hillsborough_p08 | Shell | 3840 | 1.63 | 3 / 1 / no / - | 0 / 0 / no / - |
| HoHxFSX_gLk_s1 | Hardcourt | 1920 | 1.71 | 3 / 1 / no / - | 0 / 0 / no / - |
| HoHxFSX_gLk_s2 | Hardcourt | 1920 | 1.59 | 8 / 2 / no / 24.41 | 0 / 0 / no / 61.21 |
| mpc_mixed_p02 | Shell | 3840 | 1.64 | 0 / 0 / no / - | 0 / 0 / no / - |
| mpc_mixed_p08 | Shell | 3840 | 1.63 | 0 / 0 / no / - | 0 / 0 / no / - |
| mpc_tuesday_p01 | Shell | 3840 | 2.79 | 1 / 1 / no / - | 0 / 0 / no / - |
| mpc_tuesday_p07 | Shell | 3840 | 2.81 | 0 / 0 / no / - | 0 / 0 / no / - |
| sAjkpeRq4P4 | Clay | 1920 | 3.33 | 8 / 6 / **YES** / 2.35 | 0 / 0 / no / 3.40 |
| tc8CGFxyRE8 | Hardcourt | 1920 | 2.00 | 7 / 3 / no / 46.59 | 0 / 0 / no / - |
| UHf0LeMU2pg | Hardcourt | 1920 | 3.35 | 7 / 2 / no / 60.97 | 1 / 1 / no / - |
| uR5q2cSM6AY | Hardcourt | 1920 | 3.32 | 8 / 3 / no / 20.30 | 2 / 1 / no / 27.77 |

The `stack`-tagged `e640` values (e.g. 73.79, 93.98) are **identical in both arms**
because they come from `stacked_clay_fit`, which the flag does not touch. They are
reported for completeness and carry no signal about the proposer.

## Mechanism — inspect the rejects

`eval/proposer_rejects.py` and a per-keypoint probe on gold frames. Stage of death,
CourtNet arm:

| clip | frames | **no proposal at all** | proposed | locked | proposal err (median) | after our local snap+lock |
|---|---|---|---|---|---|---|
| am_beginner | 8 | **8** | 0 | 0 | - | - |
| am_classB | 8 | **8** | 0 | 0 | - | - |
| am_indoor_hard2 | 8 | **8** | 0 | 0 | - | - |
| am_ntrp45_courtlevel | 8 | **8** | 0 | 0 | - | - |
| am_usta40 | 8 | 0 | 8 | 8 | 7.2 px | **5.9 px** |
| am_wingfield_clay | 8 | **6** | 2 | 2 | 121.7 px | 112.2 px |

**The CNN is the thing refusing.** Not `lock_quad`, not the vote: on the failing
clips `detect_court_learned` returns `None` before either runs. The keypoint probe
says why — heatmap peaks clearing the 0.40 confidence bar, of 14:

| clip | frame | peaks >= 0.40 | needed |
|---|---|---|---|
| am_beginner | 3 sampled | **2, 2, 2** | 6 (and 4 for any homography) |
| am_indoor_hard2 | 3 sampled | **2, 2, 3** | 6 |
| am_usta40 | 3 sampled | 12, 12, 12 | 6 |

Two of fourteen is not a threshold that can be loosened — four points are needed to
solve a homography at all. The upstream broadcast-trained checkpoint **does not see
these courts**. Lowering `min_points` would only trade refusals for wrong courts, and
the one record this project has never spent is zero wrong-accepted courts.

**The document's LOCAL claim did reproduce, in the one place it could be observed.**
On `am_usta40`, where CourtNet fires on 12 of 14 keypoints, the classical stage moved
its proposal **7.2 px -> 5.9 px** (median, 8 frames, vs human clicks) — the same
direction as the upstream ablation's 2.83 -> 2.23. n=1 clip; it is a direction, not a
number to bank.

## What qa returned (verbatim, relayed by the coordinator)

> **Court proposal recall = 8 / 20 gold clips = 40%.** Pre-registered before the run:
> search binds if <=60%, voting binds if >=80%. **40% -> THE SEARCH BINDS.** On 12 of
> 20 clips the shipped search never once, across 8 sampled frames, produces a court
> within 20 px of the human clicks. Robust across tolerance 20-35 px, so it does not
> hinge on where in the band the line sits.

> **Shell is where it is worst** ... **1 of 5 shell recordings** (2 of 10 clips).
> Three shell recordings — `mpc_mixed_p02`, `mpc_mixed_p08`, `mpc_tuesday_p07` —
> produce **no lock at all**. Only `flexi_franz` (2.50 m) ever reaches truth. qa
> called this *borderline* rather than rounding it up.

> Best-candidate error per clip splits into: **reached** (8 clips, 2.3-18.7 px),
> **near miss** (2: 23.1, 27.6 px), **wrong court** (7: 35.7-111.4 px), and **nothing
> produced at all** (3, all shell).

> **The mount-height mechanism is NOT established.** <2.0 m scores 33.3%, >=2.0 m
> scores 50.0% — a 16.7 pp gap against a pre-registered 40 pp bar, and confounded,
> since 8 of the 12 sub-2 m clips are shell. **Surface separates this data; height
> does not.**

> **Do not quote "9/20 truth_would_pass"** — retracted. The correct instrument says a
> court a median **4.9 px** from the clicks clears the accept gate on **19 of 20**
> references. **The criteria do not bind. The search does.**

I accepted both corrections. The A/B is split by **surface**; mount height is carried
in the per-clip table as a **covariate, not an explanatory variable**, and no
mechanism is claimed from it. My own pre-registration had a mount-height split bar in
it; it is withdrawn on qa's evidence rather than reported, because the split is
confounded by surface in this population.

**What exchanged with researcher:** nothing. `SendMessage` is **not available** —
`Error: No such tool available: SendMessage. SendMessage is disabled for this
session, in subagents as well as here` — despite two briefs asserting it works. The
coordinator relayed qa by hand. `docs/evidence/external-research-reconciled.md` was
not read or written.

## Two things this cannot fix, and did not

1. **The precision ceiling.** The line detector floors at ~6.4 px against ~5.8 px of
   human click noise. Nothing here beats that and nothing here claims to. Arm B's
   4.1 px gold median is the median of two clips it accepted out of twenty — a
   selection effect. **Finding the court at all on a cluttered court and beating the
   precision ceiling are different claims**; conflating them is a mistake made in
   this repo this week and it is not repeated.
2. **The net-overlap crossover.** Below roughly 2.0-2.2 m the net tape overlaps the
   far baseline in the image. No ordering of any two detectors recovers information
   that is not in the pixels. 12 of these 20 reference clips are below 2.0 m.

## Blast radius noted, not tested

The coordinator flagged commit `4a33635` (refiner reach `55 -> 55*w/640`), cleared as
a gate no-op at 12/20 — but **every shell reference is 3840x2160, 6x the 640-wide
gold frames, and shell is not in the gold pool**, so a shell-only effect was invisible
to its own control. This A/B changes one variable (the proposer) and cannot speak to
it. It does supply a fresh datapoint for whoever does: on the current tree the
classical arm locks **20 of 80 shell frames and accepts 0 of 10 shell clips**.

## What this licenses next

- **Not** "CNNs are robust where classical search is not" — untrue of *this*
  checkpoint on *this* footage, measured.
- The live question is whether a CourtNet **trained on amateur low-mount footage**
  proposes at all on shell. `courtnet_ft.pt` exists and was fine-tuned for our
  angles, but **17 of 20 gold clips were in its training pool**, so it cannot be
  measured on gold without self-grading. A leak-clean split is a prerequisite, not a
  detail. Not this run (retraining was out of scope).
- The flag stays, default `classical`, so that measurement is one argument away.
