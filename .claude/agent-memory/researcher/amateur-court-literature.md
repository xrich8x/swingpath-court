---
name: amateur-court-literature
description: The published court/field-registration literature surveyed against OUR regime (amateur, low-mount, indoor shell) — what transfers, what is barred by rule 3, and which sources are unreachable
metadata:
  type: project
---

Surveyed 2026-09-09 across two runs (the first killed by a usage limit).
Full writeup: `docs/evidence/court-recall-what-would-actually-move-it.md`.

**The finding, before the list: NOBODY has published a number on indoor, low-mount,
truss-and-mesh amateur court footage.** Every method below was trained and measured on
broadcast. Always say what footage a number came from.

**Why:** these get re-proposed. Each entry carries its rule-3 verdict so the next run does
not re-survey or re-suggest it.
**How to apply:** if asked "what does the literature say about court detection", answer from
this file; only go further afield than these six.

| # | Item | Verdict for us |
|---|---|---|
| 1 | **MonoTrack** court module (CVPRW 2022, arXiv 2204.01899, code `jhwang7628/monotrack`). Farin improvement: Hough -> **max-weight bipartite subgraph** to split the two line pencils (instead of hard-coded angles) -> combinatorial layout match. **73.9 -> 85.5% at IoU>0.8**, avg IoU 0.97, 40x faster. Broadcast badminton + 40 YouTube clips "outside the broadcast view". | **Only published idea that is NEW here**, and it attacks the mechanism this project called "wrong in principle" (sidelines converge, so no angular cluster). **But it inherits our C3 ceiling — 17.1 px@640 given the TRUE correspondence — and it is a seventh auto-detection branch. DO NOT FUND.** No training data needed (classical). |
| 2 | **M-LSD** (AAAI 2022 oral, arXiv 2106.00186, `navervision/mlsd`). **48.6 FPS on iPhone**, 2.5% of TP-LSD-Lite's size, MobileNetV2-family = ANE-native ops. **Released checkpoint needs NO training data.** | Best on-device story of any learned option. But it finds trusses and fence rails with MORE recall than Hough, and VP filtering is closed-by-argument here, so there is no discriminator to pair it with. Not in the negatives table. |
| 3 | **Homayounfar CVPR 2017** — branch-and-bound over all parametrised fields on a 6-class segmentation. Provably global search. | **Rule 3 BARS it as a fix**: it is "widen the seed grid" + "raise topk" in a costlier wrapper, both measured dead. Needs indoor-shell segmentation labels we do not have. |
| 4 | **TVCalib** (WACV 2023, 2207.11709), **No Bells Just Whistles** (CVPRW 2024, 2404.08401), **PnLCalib**. Camera-from-segments / keypoint+DLT, all SoccerNet broadcast. | **Closest thing to a re-proposal on the list.** Our own CourtNet arm IS this experiment: 2-3 of 14 keypoints fire on amateur, gold 12/20 -> 2/20, shell 20/80 -> 0/80. DO NOT FUND. |
| 5 | **Synthetic + domain randomisation** (SoccerSynth-Field 2503.13969, SOLD2 2104.03362). | The only published answer to "we have zero indoor-shell gold", and we own `tools/synth_truth.py`. But it is data, not a method — pays only if 1-4 is worth training, and 3/4 are barred. The hardest thing to synthesise is the exact thing we need: roof trusses and mesh. |
| 6 | **Padel / pickleball** (IDEAL 2024; ResNet50-keypoint pickleball write-ups). Right REGIME (enclosed, mesh, glass, amateur cameras). | **Nothing citable.** "No public academic datasets exist for pickleball and padel"; no reported court accuracy. Surveyed, closed. |

**arXiv 2404.06977** ("Accurate Tennis Court Line Detection on Amateur Recorded Matches",
IVPAI 2024) — its base algorithm is the **Farin joint fit this project built and killed**,
and its three additions (MTMT shadow removal, object-detector player removal, court-colour
filtering) all attack **outdoor** degradations. Closed.

## UNREACHABLE — do not retry these routes

**2404.06977 full text, 10 failed routes:** no arXiv HTML/ar5iv (404 / 307 back to `/abs`);
PDF downloads but cannot render locally (no poppler); `r.jina.ai` 403; `academia.edu` 403;
`aimodels.fyi` 403; `themoonlight.io` 429 (x3); Semantic Scholar API 429; `papers.cool`
metadata only. Everything we know of it is abstract + search-engine-indexed text.

**Already surveyed and closed, do not re-survey:** `Gholamreza/tennis_court_keypoints_dataset`
(a re-upload of yastrebksv's own 8,841-image training set — zero new information) and
CourtSide (axis-aligned boxes, no quadrilateral). See [[external-research-reconciliation]].

**Reached only at abstract depth** (treat as second-hand): TVCalib, No Bells Just Whistles,
Homayounfar, SoccerSynth-Field, SOLD2. **MonoTrack was reached IN FULL via ar5iv.**
Not read: MonoTrack's actual court code — the bipartite claim is from the paper's prose.

Related: [[court-detection-negatives]], [[external-research-reconciliation]],
[[coreml-ane-budget]]
