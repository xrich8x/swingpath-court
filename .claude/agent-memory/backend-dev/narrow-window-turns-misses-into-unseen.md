---
name: narrow-window-turns-misses-into-unseen
description: a search window of 3x tol with noise taken from the wings makes an OFF-tolerance ridge read "unseen", and unseen leaves the denominator - a miss becomes a pass (G8 BAR 3, 2026-09-22)
metadata:
  type: project
---

`camera3d._seg_hit` estimates noise (MAD) from the wings `|s| > tol` of a window `[-3 tol, +3 tol]`.
A ridge sitting just OUTSIDE tolerance lands IN the wing, inflates the MAD, and its own z collapses
to 0, so the segment reports "no ridge seen" instead of "ridge seen, off target". `score_far_stacks`
takes `frac` over SEEN segments only, so the miss leaves the denominator: sim seed 201's knock frame
(49 cm out) went from 2/6 (fail at reach 8.0) to 2/4 = 0.5 = `min_line_frac` (PASS) at the
registered 2.25, and the tracker claimed `whole_court` while 49 cm out.

**Why:** "unseen is not failed" ([[undetected-is-not-failed]]) is right for a BLANK profile, but a
window narrower than the errors you must catch manufactures blankness out of exactly those errors.
Widening the window instead lets the net tape in ([[the-net-tape-owns-the-far-lines]]) - the window
cannot be set to satisfy both on CP1's scene.

**How to apply:** any rule that drops unseen samples from a denominator needs the window to be wider
than the error it must detect PLUS the PSF, and the noise estimate must come from outside the
peak's reach. Check with a case just past tolerance, not only far past it. Also: at the registered
window the stacked profile is BLIND at every tol <= 0.50 px@720 on the clean sim scene.
