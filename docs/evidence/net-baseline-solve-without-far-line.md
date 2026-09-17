# Solving the camera from the NEAR BASELINE and the NET — never seeing the far line

> Evidence for the `net-baseline-solve-without-far-line` row in [../STATE.md](../STATE.md).
> Derived and tested 2026-09-06 (lead), from the founder's proposal: *"extrapolate the court
> based on where the net is relative to the angle of the camera, so how stretched it looks."*

## Why this is worth taking seriously

Every court failure this project has measured traces to the **far baseline**: it is the
farthest, most foreshortened, worst-resolved line, and below a ~2.0–2.2 m mount the net tape
**physically overlaps it** so no method can separate the two. 16 of 28 existing calibrations are
below that crossover.

The founder's idea sidesteps it: use the **near baseline** and the **net line** — the two rows
closest to the camera, and therefore the best-resolved — and *derive* where the far baseline
must be.

## The system is DETERMINED — four observables, four unknowns

Pinhole over a ground plane. A point at depth `d` images at `row = cy + f·H/d`, and a real width
`W` at depth `d` images as `w = f·W/d`.

The near baseline and the net line sit at a **known separation** (11.885 m) and have the **same
known real width** (10.97 m between the doubles sidelines). That gives four observables — two
rows, two widths — against four unknowns:

```
k  = w_near / w_net = (D + 11.885) / D      ->   D  = 11.885 / (k − 1)
f  = w_near · D / W
cy = (r_near − k·r_net) / (1 − k)
H  = (r_near − cy) · D / f
```

`D` is the camera's standoff behind the baseline, `f` its focal length in pixels, `cy` the
horizon row, `H` the mount height. **The width ratio alone fixes the standoff** — that is the
"how stretched it looks" the founder described, made precise.

Self-test, synthesising a camera then solving back from its four observables:

| true H | true D | width ratio k | recovered H | recovered D | error |
|---|---|---|---|---|---|
| 1.64 m | 3.0 m | 4.962 | 1.64 | 3.00 | 0.0000 m |
| 2.50 m | 3.0 m | 4.962 | 2.50 | 3.00 | 0.0000 m |
| 3.35 m | 4.0 m | 3.971 | 3.35 | 4.00 | 0.0000 m |
| 1.38 m | 2.0 m | 6.942 | 1.38 | 2.00 | 0.0000 m |

Exact. The far baseline is never used.

## Error propagation is benign — and that is the surprise

The obvious objection is amplification: a small angular error near the camera becomes a large
positional error at 23.77 m. Monte Carlo, 4,000 draws per cell, gaussian pixel noise on **all
four** observables, asking where the **extrapolated far baseline** lands:

| mount | input noise | camera-height error (median) | far-baseline row error (median) | (p90) | failures |
|---|---|---|---|---|---|
| 1.64 m | 0.5 px | 0.003 m | **0.4 px** | 0.9 | 0 |
| 1.64 m | 1.0 px | 0.005 m | **0.8 px** | 1.8 | 0 |
| 1.64 m | 2.0 px | 0.010 m | **1.5 px** | 3.6 | 0 |
| 1.64 m | 6.4 px | 0.033 m | **4.9 px** | 11.9 | 0 |
| 2.50 m | 2.0 px | 0.010 m | 1.5 px | 3.8 | 0 |
| 3.35 m | 2.0 px | 0.014 m | 1.6 px | 3.8 | 0 |
| 3.35 m | 6.4 px | 0.045 m | 5.0 px | 12.4 | 0 |

Against the shipped bar of **8.1 px** reconstruction error:

- at **≤2 px** input noise the extrapolation lands **comfortably inside** it;
- at the full **6.4 px** line-detection floor it is **inside at the median (4.9 px)** and
  **outside at p90 (~12 px)**;
- **zero solver failures** in every condition.

**And it is insensitive to mount height** — 1.64 m performs the same as 3.35 m. That is the
whole point: the occlusion problem is mount-driven, and this method is not.

## What would kill it, stated as the falsifier

**The precision of the two input lines has not been measured.** The premise is that the near
baseline and net line are well-resolved *because they are close to the camera* — plausible, and
the reason the idea is attractive, but unmeasured. The table above says the method needs
**≤2 px** on those two rows and their two widths to beat the shipped bar comfortably.

**So the falsifier is one measurement: what is the detection precision of the near baseline and
the net line specifically?** If it is ≤2 px, this is a real path. If it is at the ~6.4 px
whole-court floor, the method is borderline — median-inside, p90-outside — and would need
temporal integration to sharpen the inputs, which is exactly what the clean plate exists to do.

## Limits, stated

- Ideal pinhole, flat court, **no lens distortion**, **zero roll**, principal point centred
  horizontally. Real 0.5× ultrawide footage violates the first; the audit already fits roll
  separately and measures ±1° on real clips.
- It solves the camera, not the court's lateral placement — the sidelines still have to be
  located, and this says nothing about which pair of lines you measured.
- It assumes the net line and the doubles sidelines are both visible where they cross. **The net
  is the one line this project has repeatedly found easy to locate**, which is what makes the
  premise plausible.
- **Not a court detector.** It is a way to place the far baseline once the near baseline and net
  are known, so it composes with a human placing two lines rather than four — it does not remove
  the human.
