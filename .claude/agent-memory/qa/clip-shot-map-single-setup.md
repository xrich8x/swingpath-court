---
name: clip-shot-map-single-setup
description: Clip-structure measurement 2026-09-09 - 8/10 clips are single-setup by the pre-registered G>=6 bar, but "registrable under a similarity" is NOT "one homography holds"; the pool-size answer is N=1 (bar) vs N=4 (tight reading)
metadata:
  type: project
---

Measured 2026-09-09 for the founder's drop-or-restrict decision on the 9 clips flagged by
his blind re-review of 10 court calibrations. Evidence: `docs/evidence/clip-shot-map.md`.

**Result.** Pairwise ORB+RANSAC among the 8 `run_refs.frame_positions` frames only
(video frame 0 excluded — it is not one of the 8). `G` = largest clique.
FAIL-RESTRICT only on `HoHxFSX_gLk_s1` (G=5) and `HoHxFSX_gLk_s3` (G=4). Everything else
G=8 except `HoHxFSX_gLk_s2` at exactly 6 (borderline). **Zero FAIL-DROP.**
Pool consequence: **N=1** leaves the 20-clip pool by the bar (5%); **N=4** under a tight
reading (20%). `HoHxFSX_gLk_s3`, `bump_ntrp30`, `bump_ntrp30b` are NOT in the pool at all.

**Why:** the founder must restate the fraction in writing before anything is re-measured.

**How to apply:** the lesson that outlives the task is the instrument limitation, and it
is general. An ORB/RANSAC **similarity** edge only proves the two frames share a
registrable background. That is satisfied by a camera that pans/zooms 188 px@640 and 40%
(`A7vXlWIlyrI`), where one homography plainly cannot hold. So a "same setup" grouping
built on similarity screens out clips **edited across venues**, not clips whose **camera
moved** — necessary, never sufficient. If a future run needs "one homography holds",
add the intra-group displacement against `WRONG_PX_640 = 20.0` as a second quantity
(reported as `S20` here) rather than loosening or tightening the edge test.

Two methods that worked and are worth repeating:
- **The negative control is what validates a grouping**, not the null and positive. A
  frame vs a frame from a *different clip* must produce NO edge; it did on 11/11. Null
  (0.000) and +8px (7.91-8.05) only prove the estimator runs.
- **Compute CC and CLIQUE both** so non-transitivity is measured rather than assumed
  away. Here `CC_max == G` on all 12 clips, so no verdict depended on the choice.
- `S20` independently reproduced run 3's cut positions (bump_ntrp30 step at 508,
  UHf0LeMU2pg at 4198) from a different direction — cross-instrument agreement on cut
  location is the reason to trust the grouping.

Related: [[camera-motion-vs-court-agreement]], [[corner-audit-frame-choice-risk]],
[[court-proposal-recall-search-binds]].
