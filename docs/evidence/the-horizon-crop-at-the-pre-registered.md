# The horizon crop (movers.crop_row) at the pre-registered k = 1.0

> Evidence for the `the-horizon-crop-at-the-pre-registered` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**Safe but inert: a crop is proposed on 1 of 20 gold clips**, and that one removes the top 20 rows of 360. The margin `k · spread` is ~one whole court depth above the far baseline, so the row lands off-frame. Capping detections at 4 (the rules of the game) halved the blob count and changed nothing, which is what identifies the margin rather than the mover detection. `k` deliberately **not** re-tuned — that is the drift the blind holdout exists to stop.
