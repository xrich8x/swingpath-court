---
name: renderers-cannot-place-subpixel-paint
description: A point-sampled renderer misplaces a sub-pixel line by up to half a pixel at ANY supersampling; jitter + PSF-before-binning is the only order that works
metadata:
  type: project
---

**A synthetic renderer that point-samples on a fixed sub-sample grid and applies the PSF
AFTER binning CANNOT place paint thinner than a pixel, at any supersampling rate.** Two
independent faults, both measured on `tools/court_track_sim.py` (G8, 2026-09-19), true
camera, no noise, 1920x1080:

- **Phase, not resolution.** A 0.19 px band is hit or missed by whichever fixed sub-sample
  lands in it. The far baseline read **0.49 DN** and the far service line **21.5 DN** where
  both should read ~7.9. Raising `ss` does not converge the amplitude, because a
  near-horizontal line has a near-constant sub-pixel phase along its whole length and
  stacking cannot average it: ss 4 / 8 / 16 gave 10.6 / 5.1 / 7.9 DN.
- **Binning before blurring quantises POSITION.** A line inside one pixel row collapses onto
  that row's centre. The far baseline read **0.5 px off at 1280x720 even at ss=8**.

**The fix is CP1's order and only that order:** jittered stratified sub-samples (coverage
becomes unbiased) plus the PSF applied at sub-sample resolution, then bin. At 1080p that
works at **ss=2** — 0.97 s/frame, only 33% over the broken version — giving offsets within
0.05 px.

**Why:** CP1's evidence file already records the same deviation from its own spec §7 for the
same reason ("the renderer applies the PSF BEFORE pixel binning... a forced deviation... which
erased sub-pixel position"). The trap was re-paid on a second renderer 6 weeks later.

**How to apply:** before measuring ANYTHING sub-pixel on rendered imagery, probe the true
camera's stacked normal profile on the thinnest line in the scene and check the amplitude
against `contrast * width_px / (sigma * sqrt(2*pi))`. If it is off by more than ~30%, the
renderer is aliasing and the measurement is of the renderer, not the algorithm. Changing the
render order changes the SCENE — gate it behind a flag whose default reproduces every prior
number, exactly as [[a-second-profile-never-an-edit]] does for the encoder.
