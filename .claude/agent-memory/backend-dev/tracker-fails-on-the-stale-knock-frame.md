---
name: tracker-fails-on-the-stale-knock-frame
description: G9 (2026-09-22) - camtrack is precise (1.45 cm p90, 1-frame recovery) but claims a lock on 5/6 knock frames 41-65 cm out; x3/x4 knocks lost honestly
metadata:
  type: project
---

G9, the fixed tracker's first pre-registered gate, KILLed on the silent-failure bar, not on precision.
On fresh seeds 500-505 under `--subpixel`, far lines OFF: every line p90 1.45 cm, steady jump 0.15 px,
the x1 knock recovered in 1 frame on 6/6. But **5 of 6 knock frames report `locked` (scope `near_half`)
while 41-65 cm out**, each for exactly that one frame; one of them also has a NEAR line past 10 cm.
The x3/x4 knocks are lost for good on 6/6 runs with 0 wrong locks.

**Why:** the dev/qa rate ("1 wrong lock in 3 seeds") came from 3-seed runs and understated a 5-in-6
effect. Small-seed dev numbers make rare-looking failures that are really common.

**How to apply:** the next tracker work is lock LOGIC at a shock (a hold-off when predicted motion or
flow residual jumps), not precision. It needs its own pre-registration on seeds other than 500-505.
Any far-line remedy must first clear [[narrow-window-turns-misses-into-unseen]] and
[[the-net-tape-owns-the-far-lines]]. Seed sets spent so far: 100-102, 200-202, 300-305, 400-402, 500-505.
