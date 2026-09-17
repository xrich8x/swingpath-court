# Snapping a near-correct court onto the detected lines

> Evidence for the `snapping-a-near-correct-court-onto-the` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

Sidesteps the grouping problem and fails differently: **matching the four model lines independently lets them pick a mutually inconsistent set**, and intersecting it gives a wild quad. Median distance from truth: seed 9.8 → refiner **8.4** → snap **70.5**. Tightening the tolerance only makes it refuse (10.0 = the seed unchanged). A correct version needs JOINT line-to-model assignment solved with the homography — a real build, untested here.
