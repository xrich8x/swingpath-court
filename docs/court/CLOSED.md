# Court detection — CLOSED

**Things tried here that did NOT work, and the number that killed each one.**

Read this before proposing anything in this area. Hard rule 3: **do not re-propose these.** Nine
distinct ideas in this project have been re-proposed at least once, each costing a run to re-kill.

**The code is gone, not lost.** Where a row names a deleted file, recover it with:

```bash
git log --diff-filter=D --oneline -- <path>     # find the commit that removed it
git show <sha>^:<path>                          # print the file as it last existed
```

A row here is a verdict. The mechanism and the war story live in `docs/evidence/`.

| What was tried | What we did | The result that killed it | Deleted code | Evidence |
|---|---|---|---|---|
| **Building the court quad from DETECTED LINES** | Cluster detected lines by angle, construct the quad | **Wrong in principle, not mis-tuned** - under perspective the two doubles sidelines converge, so they form no angular cluster. Best quad **68-256 px** from truth vs the lattice's 7-20 | - | [building-the-court-quad-from-the-detected](../evidence/building-the-court-quad-from-the-detected.md) |
| **Snapping a near-correct court onto detected lines** | Refine, then snap to nearest lines | Median distance from truth: seed 9.8 -> refiner **8.4** -> snap **70.5**. Needs joint line-to-model assignment | `eval/line_snap.py` | [snapping-a-near-correct-court-onto-the](../evidence/snapping-a-near-correct-court-onto-the.md) |
| **Raising `topk` so more seeds get refined** | topk 12 -> 40 -> 150 | Moves **no clip** and costs **7x compute** (32 s -> 229 s per 4 frames) | - | [raising-topk-so-more-seeds-get-refined](../evidence/raising-topk-so-more-seeds-get-refined.md) |
| **Removing the pose-prior weight from seed RANKING** | Ablate the prior | No clip improves; the prior is not what buries the true seed | - | [removing-the-pose-prior-weight-from-the](../evidence/removing-the-pose-prior-weight-from-the.md) |
| **Reachability - that refinement cannot travel seed -> true court** | Measure nearest-seed distance vs refiner reach | **STOPPING RULE FIRED.** On **31 of 38** clips the nearest seed is already within reach. The brief predicted the opposite in advance | `eval/seed_reach.py, eval/reach_ab.py` | [reachability](../evidence/reachability.md) |
| **Narrowing `EVID_BAND`** | Sweep the evidence band | **The band is INERT** - the hypothesis the whole brief was built around is refuted | `eval/evid_band_sweep.py` | [narrowing-evid-band-so-clutter-near-a](../evidence/narrowing-evid-band-so-clutter-near-a.md) |
| **Observability from geometry instead of nearby paint** | Score seeds by geometric observability | **+0.000 margin** | - | [observability-from-geometry-instead-of-nearby-paint](../evidence/observability-from-geometry-instead-of-nearby-paint.md) |
| **Behind-camera projection inflating the denominator** | Audit projected points behind the camera | **0.0%** of samples affected | `eval/behind_camera.py` | [behind-camera-projection-inflating-the-denominator](../evidence/behind-camera-projection-inflating-the-denominator.md) |
| **The low true-court score being human click error** | Sweep `tol` x0.5 -> x4 | No clip shows the steep threshold a click-error explanation needs | `eval/tol_sweep.py` | [the-low-true-court-score-being-human](../evidence/the-low-true-court-score-being-human.md) |
| **Player-foot gate as a court-negation criterion** | Vote on whether feet fall inside the candidate court | **DEAD - no discriminative power.** Converts zero reference clips | `eval/foot_gate_power.py` | [the-player-foot-gate-as-a-wrong](../evidence/the-player-foot-gate-as-a-wrong.md) |
| **The far player found by MOTION as an identity signal** | Nearest `movers` blob to a post-hoc far-player box | **FAILS the pre-registered gate.** Median **5.751** box-heights, **7 of 15** frames within 1.5 (bar: <=1.5 on >=10/15). The random-blob null control also fails | `eval/far_player_motion_gate.py` | [far-player-motion-gate-result](../evidence/far-player-motion-gate-result.md) |
| **Widening / height-scaling `AGREE_PX`** | Widen the agreement threshold | The resolution artefact is real but widening does not recover the disagreement | `eval/agree_sweep.py` | [widening-height-scaling-agree-px-to-recover](../evidence/widening-height-scaling-agree-px-to-recover.md) |
| **The horizon crop at `k = 1.0`** | Crop above the horizon before search | **Safe but inert** | `eval/crop_safety.py` | [the-horizon-crop-at-the-pre-registered](../evidence/the-horizon-crop-at-the-pre-registered.md) |
| **Improving CourtNet for auto-calibration** | Fine-tune the vendored CNN | **Wrong target** - CourtNet is Tier 2; `courtfit` consensus is Tier 1 and beats it | - | - |
| **Single-frame court auto-seed in the setup tool** | Seed the tool from one frame | **7 of 10 worse** than starting from a blank rectangle; only multi-frame consensus separates the cases | - | [single-frame-court-auto-seed-in-the](../evidence/single-frame-court-auto-seed-in-the.md) |
| **Lowering the court consensus bar 6/8 -> 5/8** | Relax the vote | **GATE FAILS** - the one 5-vote clip is wrong by 68.7 px | - | [lowering-the-court-consensus-bar-6-8](../evidence/lowering-the-court-consensus-bar-6-8.md) |
| **CNN-global -> classical-local** | CourtNet proposes globally, classical refines | **FAILS.** Premise supported, remedy not available | - | [cnn-global-classical-local](../evidence/cnn-global-classical-local.md) |
| **Least-squares over ALL matched line correspondences** | Fit to every correspondence, not 4 points | **FAILS the pre-registered bar.** The 4-point control gives **17.10 px@640** with an identical survivor set and **0.00 px** max difference | `eval/corr_ls_fit.py` | [least-squares-court-fit](../evidence/least-squares-court-fit.md) |
| **Net POST and fitted-hfov as calibration references** | Detect the post; fit hfov | **BOTH FAIL - gates four and five.** The post's per-pixel sensitivity is 15% better than the tape's and it still loses on row precision by **~7x**. Scores **3 of 11 = 27%** against a 67% bar | - | [net-post-detector](../evidence/net-post-detector.md) |
| **Gravity/arc as a calibration reference** | Fit apparent `g` to recover scale | **DO NOT BUILD.** +/-15-25% precision from pixel noise alone vs the net tape's met 10% bar | - | [gravity-arc-pilot](../evidence/gravity-arc-pilot.md) |
| **Clean plate / MTI to sharpen inputs** | Temporal median background | **RETIRED** - the current no-plate baseline already beats its 11.5 px | - | [cleanplate-mti-measured](../evidence/cleanplate-mti-measured.md) |
| **Court AUTO-detection generally** — *REOPENED AS A GOAL by the founder 2026-09-17: v1's court must be found automatically. The verdict below still binds on the branches it names; a new automatic route must differ from them (rule 3).* | Every classical and learned branch tried | **CLOSED for v1.** No branch reaches the shipped **8.1 px** bar; the line detector's ~**6.4 px** disagreement with truth is the ceiling. Manual four-corner setup is the product answer | - | [court-detection-path-after-the-line-ceiling](../evidence/court-detection-path-after-the-line-ceiling.md) |
