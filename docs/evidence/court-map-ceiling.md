# P8 C1 — does the four-tap court model place every line? No. Tap precision is what binds.

**Run 2026-09-16 by the lead** (`tools/court_map_ceiling.py`, 39 configurations × 400 seeded trials,
17 s). Pre-registered in `.claude/journals/lead.md` ("P8") before any run, at the founder's request
to "test to see if the 3d spatial mapping of the court works".

**WHAT EVERY NUMBER HERE WAS MEASURED AGAINST:** exact court geometry — the true coordinates of
points sampled along every painted line — projected through a known synthetic camera. No labels, no
model output, no footage.

**WHAT PINS THE COURT MODEL:** four coplanar tapped doubles corners and the regulation doubles
rectangle; for the 3D camera only, also the ASSUMED horizontal field of view.

**Why it was needed.** P1 tested the ball against a PERFECT court — exact corners, exact hfov. Every
P1 number is therefore conditional on a court model nobody had measured. This is that measurement.

## Method

A camera from `height_curve.frame_the_court` (centre-line, 6 m setback, 1920×1080, hfov 100°, pitch
solved to frame the court). The four corner pixels are perturbed by tap noise, the model is rebuilt,
and for 11 points along each of the 14 painted lines (near and far halves separate) we ask: a ball
sitting exactly on that line shows at its true pixel — where does the rebuilt model put it? Error is
taken **perpendicular to the line**, the component that changes a call, and the **worst of the 11
points** per trial is kept. p90 is over 400 trials.

**Two maps are graded, and the bar required BOTH to pass** (decided before the run):
- **2d** — `calibration.homography_from_landmarks` + `image_to_court`, the ground map the shipped
  line call uses. It never sees hfov.
- **3d** — `bridge.camera_from_court_corners` intersected with `z = 0`, the 6-DOF camera P1's 3D
  arm uses. **It takes hfov as an INPUT (default 70°)**, so hfov error is swept for it.

**Tap noise**, per-axis σ at 1920 wide: 0 / 1 / 2 / 4 px, plus the **realistic rung, 14.78 px** — the
published human corner-click spread of 5.8 px @640, read as the median radius of an isotropic
Gaussian (σ = 5.8/√(2 ln 2) = 4.93 px @640) and scaled ×3. **That scaling assumes click precision is a
fixed fraction of the frame, which a zoomed tap on a phone may beat.** It does not decide the
verdict: 1 px already fails (below).

**Internal control:** with zero tap noise and exact hfov, both maps place every line on itself (2d
exactly; 3d to 5 µm, float32 PnP) and recover the camera height as 3.000 m. Pinned by
`backend/tests/test_court_map_ceiling.py`.

## THE VERDICT

| Bar (pre-registered) | Result | Verdict |
|---|---|---|
| **PASS:** realistic tap noise, exact hfov, p90 ≤ 5 cm on EVERY line, BOTH maps | worst line at 3 m: **14.1 m** (2d), **7.2 m** (3d) | **FAIL** |
| **KILL:** any line > 10 cm at p90 at realistic tap noise | **every line, every mount, both maps** — the best line anywhere is the near centre service line on the 3d map at 3 m, **0.26 m** | **FIRED** |

**Capability 1, as a manual four-corner tap, cannot support SPEC §3 on any line at the tap precision
a person delivers.** The court model alone spends more than the whole 10 cm call budget before the
ball is even considered.

## It is not the model. It is the tap — and the precision required is about a tenth of a pixel.

Error is **linear in tap noise** (far baseline, 2d, 3 m: 0.692 / 0.677 / 0.673 m per px at 1 / 2 /
4 px), so the tap precision each line needs is the bar divided by its 1-px error:

**Mount 3.0 m** — p90 perpendicular error (m), and the per-axis tap σ that would reach 5 cm:

| Line | 2d @1 px | 3d @1 px | 2d @human | 3d @human | tap needed (2d) | (3d) |
|---|---|---|---|---|---|---|
| near baseline | 0.034 | 0.034 | 0.51 | 0.50 | **1.46 px** | 1.48 px |
| near singles sideline L | 0.052 | 0.037 | 0.82 | 0.56 | 0.96 px | 1.36 px |
| near doubles sideline R | 0.068 | 0.054 | 1.24 | 0.80 | 0.74 px | 0.92 px |
| near centre service | 0.081 | 0.018 | 1.19 | 0.26 | 0.62 px | **2.85 px** |
| far centre service | 0.063 | 0.032 | 0.98 | 0.46 | 0.79 px | 1.58 px |
| far singles sideline L | 0.089 | 0.076 | 1.35 | 1.16 | 0.56 px | 0.66 px |
| far doubles sideline R | 0.133 | 0.105 | 2.76 | 1.54 | 0.38 px | 0.48 px |
| near service line | 0.108 | 0.065 | 1.65 | 0.93 | 0.46 px | 0.77 px |
| **far service line** | 0.411 | 0.295 | 6.89 | 4.44 | **0.12 px** | 0.17 px |
| **far baseline** | **0.692** | **0.470** | **14.13** | **7.24** | **0.07 px** | **0.11 px** |

Lines passing 5 cm even at **1 px** of tap noise: **1/14 (2d), 6/14 (3d)** at 3 m; 0/14 and 2/14 at
1.5 m; 7/14 and 8/14 at 8 m. The far baseline needs **0.07-0.11 px** at 3 m and **0.20-0.24 px** even
from an 8 m mount. **No human tap reaches that: the realistic rung is 130-210x coarser, and a magnifier will not close
a gap that size.**

**The prediction written before the run held:** the far lines fail, by the same `D²/(f·h)` geometry
as R1 — a pixel of far-corner tap error moves the far baseline tens of centimetres along the camera
ray (0.47-0.69 m at p90, worst point, at 3 m). The far baseline is the line the four taps pin most
directly, and it is still the worst, because the camera barely resolves distance in that direction.

**Full-court tables for 1.5 m and 8.0 m** are in `data/output/court_map_ceiling.json`; the shape is the
same, scaled by mount height (far baseline 1-px error: 1.38 m at 1.5 m, 0.69 m at 3 m, 0.25 m at
8 m, 2d).

## The 3D camera beats the flat map — only if the field of view is known

The 6-DOF camera with a known focal length has fewer free parameters than an 8-DOF homography, so
it absorbs tap noise better: realistic-tap far baseline **7.2 m vs 14.1 m** at 3 m, and on the near
centre service line **0.26 m vs 1.19 m**.

**But its advantage is bought with the hfov input.** With PERFECT taps at 3 m:

| hfov error | 3d worst p90 | camera height believed |
|---|---|---|
| −10° | 0.71 m | 3.14 m |
| −5° | 0.37 m | 3.07 m |
| +5° | 0.41 m | 2.93 m |
| +10° | 0.86 m | 2.87 m |

**A 5° field-of-view error alone costs ~40 cm, with the taps perfect.** The flat map is immune (it
never uses hfov). P1's 3D numbers assumed the hfov exactly; a real app must read it from the device,
and the P5 protocol's framing A is the 0.5x ultra-wide, whose distortion this pinhole rig does not
model at all.

## The obvious remedy is already closed, and the reason matters

Tap noise could in principle be averaged away by fitting the court to the hundreds of pixels along
the painted lines. `docs/court/CLOSED.md` has measured that family: **snapping onto detected lines
failed** (median 70.5 px@640 from truth), **least-squares over all line correspondences failed** and
was identical to the 4-point control at **17.10 px@640**, and the refiner reaches **8.4 px@640**.
Scaled to 1920 wide that is ~25, ~51 and ~210 px against the **0.07-0.11 px** the far baseline needs
at 3 m — **roughly 250x to 2,000x short.**

**And none of them could have shown sub-pixel accuracy if it existed:** they were scored against
human corner clicks whose own spread is ~5.8 px@640 (~17 px at 1920), **roughly 200 times coarser**
than the requirement.
**Rule 3: this is not re-proposed here.** A route to ~0.1 px would need both a new mechanism and a
truth set able to resolve it — the P5 visit's tape-measured fiducials are the first instrument in
this project that could.

## What it means

1. **Capability 1 as specified does not work to SPEC §3's precision.** The four-tap court model
   alone exceeds 10 cm on every line at human tap precision, and on the far across-court lines it
   exceeds 10 cm at any precision a human can deliver.
2. **It compounds P1, it does not replace it.** P1 failed with a perfect court. With a realistic
   court, the far lines are lost twice over, both times along the same blind axis.
3. **It independently corroborates pm's per-line §3 shape from the court side.** pm proposed no v1
   accuracy bar for across-court lines (§3.2); the court model reaches the same place without
   touching the ball. The along-court lines at 3 m need 0.4-1.4 px taps — demanding, not absurd.
4. **The field of view is a first-class input**, not a default. The shipped 70° default is a
   ~40-cm-class error source per 5° on its own.

## Limits

- **Synthetic:** pinhole camera, no lens distortion, roll 0, isotropic Gaussian taps, one setback
  (6 m) and one hfov (100°). Framing B (the far-half telephoto from P5) is **not testable here**:
  its near corners are out of frame, so the four-tap cannot be used at all.
- **Worst-of-11-points** per line is a strict metric; a median-point metric would read lower.
- **The realistic tap rung is an assumption** (above). The linear table lets any other tap precision
  be read off directly, and the verdict holds at 1 px.
- **C2 (real footage vs the 20-file court gold) and C3 (the court visit's fiducials) are still to
  run.** C3 is the only one that can measure real tap precision in metres.

**Raw results:** `data/output/court_map_ceiling.json`. Reproduce:
`cd backend && .venv/Scripts/python.exe ../tools/court_map_ceiling.py --n 400 --seed 0` (17 s).
