---
name: external-research-reconciliation
description: What the founder's 8 Sep 2026 external research doc got right and wrong about court detection, verified first-hand against HuggingFace/GitHub — do not re-verify these
metadata:
  type: project
---

Reconciled 2026-09-09. Full write-up: `docs/evidence/external-research-reconciled.md`.
**These were verified first-hand from the sources. Do not spend calls re-fetching them.**

## Upstream `yastrebksv/TennisCourtDetector` — the facts, checked

- **0.963 precision / 0.961 accuracy / median 1.83 px**, where "accurate" = within **7 px** at
  **1280x720**, on a **25% validation split of the same 8,841-image pool it trained on**.
  YouTube tournament highlights, every 50th frame, manually filtered, all three surfaces.
  **This is an in-distribution BROADCAST validation number, not a held-out-domain number.**
- **15 output channels = 14 keypoints + court centre, "for better convergence" — UPSTREAM'S OWN
  ARCHITECTURE**, not something we added. `_courtnet.py` mirrors it and says it is kept
  "byte-for-byte compatible with the published checkpoint". Any recommendation to "add a
  synthetic court-centre keypoint" is already done, twice over.
- Pipeline is **CNN-global → classical-local**: refinement extracts white pixels, detects lines,
  computes intersections; then a homography from 4 predicted + 4 reference points relocates
  points. Ablation **base 0.933 → combined 0.961 (+2.8 pts)**. The per-step split is NOT
  published in what I could reach — do not repeat "refinement buys accuracy, homography buys
  reliability" as established.
- Repo health confirmed: **3 commits, 4 open issues, 272 stars, 69 forks, weights on Google
  Drive.** ("Unanswered" not confirmed — I did not open the issues.)

## `Gholamreza/tennis_court_keypoints_dataset` — the finding that matters

**It is a re-upload of yastrebksv's own training set** — 8,841 images, 14 points, 1280x720,
75/25, digit for digit. **So it carries ZERO information we do not already have inside
`court_detector.pt`.** Fine-tuning on it re-fits the checkpoint's own distribution and moves
away from amateur footage. Licence **MIT** on the re-upload (the original's licence unverified).
Broadcast-only: CONFIRMED. "Semi-automatic" and the selection-effect bias: **NOT confirmed —
neither card says it.** Plausible, unverified; do not cite as fact.

## `Davidsv/CourtSide-Computer-Vision-*` — out of scope for court, permanently

- v0.1: one class `tennis_ball`, mAP@50 **67.87%** on **62 validation images**.
- v1: 10 classes, mAP@50 92.13% on unnamed "combined datasets". Detects the court as
  **axis-aligned bounding boxes over REGIONS** (court, service boxes, alleys, net, dead zones)
  — **no lines, no keypoints**. An axis-aligned box over a perspective quadrilateral discards
  exactly the shape a homography needs. **It cannot calibrate anything.**
- The "85.6% vs 67.87%" contradiction is REAL on the cards but is a **ball**-model version
  mix-up (v0.2 most likely). Both YOLOv11n 2.6M, MIT.

## The central claim, decided

Doc: *upstream runs CNN-global → classical-local, we run classical-global → CNN fallback;
our shell failure is a global-search failure, unifying five prior rejections.*

- **DIAGNOSIS CONTRADICTED (0.80).** The correct court is **generated (7/10)**, **reachable
  (31/38, stopping rule fired)** and **recognised (9/10)**, then lost at the consensus vote —
  13 of 18 clips disagree about **WIDTH**. Widening the seed grid *reached* the right courts and
  got **every one wrong**. That is "found it and lost the vote", not "never found it".
- **PRESCRIPTION NOT RETIRED (0.90).** Our closure binds the **line detector** (~6.4 px vs
  ~5.8 px click noise) — that is *their stage 2*, not their stage 1. **Never cite the 6.4 px
  ceiling as an argument against CNN-global localisation; it is the wrong number for that
  claim.** Expected value is still low because the payload (a correct global proposal) is the
  thing we already have.
- **The one number that would narrow me: shell-specific proposal recall.** Pooled 7/10 and
  31/38 are across surfaces; the doc's claim is about shell.

## A13 cost of the court CNN — priced 2026-09-09, nobody had

**≈151 G MACs ≈ 300 GFLOPs/frame**, summed layer by layer from `_courtnet.py`. But court
detection is **one-time** (8 frames per video, `docs/modules.md:130`), so ~**2-5 s one-off** on
an A13 and **no thermal exposure at all**. ~11M params ≈ **22 MB fp16**. **Operator coverage is
zero-risk**: only Conv2d / ReLU / BatchNorm2d / MaxPool2d / Upsample-nearest — all ANE-native,
BatchNorm folds at export. Timing half is judgement (0.6); operator half is firm (0.90).
Consistent with STATE: a learned court net is **strictly easier to ship on iOS** than the
2,900-line classical pipeline, which has no conversion toolchain at all.

Related: [[court-detection-negatives]], [[coreml-ane-budget]], [[open-questions]]
