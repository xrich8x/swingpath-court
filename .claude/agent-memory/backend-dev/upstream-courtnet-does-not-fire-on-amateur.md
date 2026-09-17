---
name: upstream-courtnet-does-not-fire-on-amateur
description: The upstream court_detector.pt emits NO proposal on amateur/shell clips - 2-3 of 14 keypoints clear 0.40 - so CNN-global ordering FAILED 12/20 -> 2/20
metadata:
  type: project
---

Measured 2026-09-09. The **CNN-global -> classical-local** ordering flip (the top
item in the founder's external research doc) is built behind
`courtfit.auto_fit_frame(..., proposer="courtnet")`, default unchanged, and it
**FAILED its pre-registered bar**:

- gold set: **12/20 -> 2/20** accepted (median 8.1 -> 4.1 px, zero wrong-accepted both)
- reference clips: **2/20 -> 0/20**; **3 of 160** frames locked vs **89**
- shell (10 clips, all 3840x2160): **0 of 80** frames locked

**Why:** the CNN refuses *before* our 6-DOF gate or the vote ever run.
`detect_court_learned` returns None because only **2-3 of 14** heatmap peaks clear
the 0.40 bar on amateur/low-mount footage (min_points is 6; **4** are needed for any
homography). Not a tunable threshold. The upstream `court_detector.pt` is
broadcast-trained and does not see these courts.

**The premise was still right** - qa measured proposal recall **8/20 = 40%**, so the
global search does bind, worst on shell. A supported premise plus an unavailable
remedy: keep those apart.

**The document's LOCAL claim reproduced** where it could be seen: on `am_usta40`,
where the CNN fires on 12/14 keypoints, our classical snap+lock moved its proposal
**7.2 -> 5.9 px** (upstream's ablation direction, 2.83 -> 2.23). n=1 clip.

**Why:** the research doc's ablation was measured on the upstream val split
(broadcast angles); nothing in it says the model reaches a 1.4 m phone mount in an
indoor shell.

**How to apply:** do not re-propose CourtNet as the global proposer with this
checkpoint. The only live version of the idea needs a CourtNet **trained on amateur
low-mount footage** - and `courtnet_ft.pt` cannot answer it, because 17 of 20 gold
clips were in its training pool. Leak-clean split first. See
[[courtnet-weights-silently-substitute]] and
[[court-fit-ceiling-is-the-lines]].
