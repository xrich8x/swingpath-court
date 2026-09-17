# P0-3 — a native-resolution crop around the contact DOES find the far player, and
# the variable is UPSCALE, not crop size (measured 2026-08-28)

> Evidence for the `p0-3-crop-around-contact` row in [docs/STATE.md](../STATE.md).
> Runs the P0-3 arm of the approved iOS plan
> ([mobile-viability-audit.md](mobile-viability-audit.md)) after P0-2 closed the
> other route ([pose-downscale-far-player.md](pose-downscale-far-player.md)).
>
> **STATUS: PROVISIONAL. AWAITING VISUAL REVIEW BY A HUMAN.** No PASS is recorded in
> STATE. The first P0-3 probe's 78.8% survived for days because nobody rendered the
> frames; the contact sheets below exist so that cannot happen twice, and the number
> is not a result until someone has looked at them.

**Measured against:** ball-derived far-end contacts and a calibration-free
person-specific test. Not against human pose labels — this is a DETECTION rate at a
known location, not pose accuracy.

**Stage:** raw pose detections, BEFORE `select_players_on_court` and BEFORE
`_reject_static_player`. **These numbers are not comparable with the 11.0% in
[pose-downscale-far-player.md](pose-downscale-far-player.md)** — different
denominator (far-end contact frames, not all pose frames) and a different acceptance
test. Nor should they be: that 11.0% is itself withdrawn (see below).

---

## The three defects in the first probe, and what replaced each

| Defect | First probe | This probe |
|---|---|---|
| **Population** | `hit_xy[1] > court.NET_Y` — the ball's GROUND-projected contact. The ball is ~1 m up and the camera is behind the near baseline, so near contacts project past the net. It called **193 of 196** yt_match40 contacts "far". | A far-end hit is a local **MINIMUM of the ball's raw IMAGE y-track** (least-squares slope over ±5 processed frames, min \|slope\| 0.8 px/frame scaled by `height/720`, ≥3 detections per side). No homography anywhere. `tools/p0_3_population.py` |
| **Not person-specific** | "does ANY person box overlap the 448 px region" — which the near player satisfies almost regardless. | A detection counts only if **its own keypoint-hull box, grown 25%, contains the contact point**, AND its height is ≤ half the tallest person the control found, AND it is **not** that person (IoU < 0.2, centre outside). Identical test on every arm. |
| **No same-run control** | Compared against a figure from another pass. | The full-frame control is one more arm of the same pass over the same frames at the same stage. |

**A fourth defect, found while rebuilding.** The first probe indexed frames as
`t_hit_s * match["video"]["fps"]`. That field is the **effective** (processed) frame
rate, not the source rate, so on `am_hard_utr` (60 fps source, `frame_step` 2) it
seeked to half the intended time. Here `processed_index = round(t_hit_s * fps_eff)`
indexes the perception cache directly and `source_frame = processed_index *
frame_step` is decoded **sequentially**, never seeked.

**The old criterion, sized.** On the 71 yt_match40 contacts this population can
decide, `hit_xy[1] > NET_Y` calls **100.0%** of them far-half. On `am_hard_utr`,
51.1%. That is the projection artefact, measured.

---

## Population — report it before the result, because it is thin

| Clip | Shots | far | near | undecided | Usable |
|---|---|---|---|---|---|
| `yt_match40` | 196 | **25** | 46 | 125 | yes, marginally |
| `am_hard_utr` | 120 | **12** | 33 | 75 | **no — see below** |

`n = 25` resolves a large effect and nothing smaller. It does. `n = 12` does not,
and inspection of `p0_3_sheet_am_hard_utr_crop192at640_x.png` shows several anchors
sitting on **a tennis ball lying on the court** rather than on a contact — the
static-fixture false lock. **`am_hard_utr` is reported here for completeness and
should not be used to conclude anything.**

The `undecided` majority is a known property of the criterion on a LOW camera: when
the camera is near ball height, a lofted ball's trajectory **apex** is also a local
image-y minimum, so the test cannot separate every apex from every far contact. It
rejects rather than guesses. Contamination that survives dilutes every arm equally.

---

## Result — `yt_match40`, n = 25 far-end contacts

### The pre-registered test (box grown 25% must contain the contact anchor)

| Arm | Upscale | Found | Rate |
|---|---|---|---|
| **control, full frame @1280 (yolo11m)** | 1.00× | **0/25** | **0.0%** |
| crop192 @192 (yolo11m) | 1.00× | 0/25 | 0.0% |
| crop192 @640 (yolo11m) | 3.33× | 1/25 | 4.0% |
| **crop192 @640 (yolo11x)** | 3.33× | **2/25** | **8.0%** |
| crop320 @320 / @640, crop448 @448 / @640, both models | 1.00–2.00× | 0/25 | 0.0% |

### The same runs, post-hoc, with the anchor tolerance relaxed

Reading the contact sheets showed the strict test is dominated by **how precisely
the ball anchors the contact**, not by whether the far player was found: the crop
arms put a box on a 30 px person 20–50 px from the anchor and the strict test throws
it away. `tools/p0_3_tolerance_sweep.py` makes that dependence visible. **Everything
in this table except the "pre-registered" column is POST-HOC and must be labelled so
wherever it is quoted.**

| Arm | Far-sized non-near person found anywhere in the crop | Within 1.5 box-heights of the anchor | Median box height |
|---|---|---|---|
| **control, full frame @1280** | **0/25** | **0/25** | — |
| crop192 @640 (yolo11m) | 10/25 | 8/25 | 33.7 px |
| **crop192 @640 (yolo11x)** | **15/25** | **14/25** | 32.0 px |

**0/25 against 15/25 is not a marginal effect.** The full 1280 frame does not detect
the far player on this clip at a far-end contact — not once, at any tolerance. A
192 px native crop fed at 640 detects a far-player-sized person in 60% of them.

---

## The variable is UPSCALE FACTOR, not crop size (exploratory follow-up)

Added after seeing the above, so **exploratory, not pre-registered**: extra arms at
`imgsz=1280`, which separates "crop" from "how big the player is in the tensor".
Effective height = median detected box height (~30–34 px native) × the arm's upscale.

| Upscale | Arm | Player px in the tensor | Found (any) |
|---|---|---|---|
| 1.00× | full @1280; crop192@192; crop320@320; crop448@448 | ~32 | **0** |
| 1.43× | crop448 @640 | ~46 | 0–1 |
| 2.00× | crop320 @640 | ~64 | 1 |
| 2.86× | crop448 @1280 | ~90 | 5 |
| **3.33×** | **crop192 @640** | **~107–112** | **10–15** |
| **4.00×** | **crop320 @1280** | **~135** | **13** |
| 6.67× | crop192 @1280 | ~203 | 6 |

The curve is unimodal and peaks at roughly **100–140 px of player in the model
input**. Below ~90 px nothing is found; above ~200 px it degrades again (upsampling
a 30 px person 6.7× adds no information and costs context).

Two consequences worth keeping:

- **Crop size 192 and 320 both work** — at 3.33× and 4.00× respectively. It is not
  the crop that matters, it is the ratio.
- **The cheapest good arm is also the best.** `crop192@640` beats `crop192@1280`
  while costing 4× less. Nothing here argues for a larger input tensor.

---

## `am_hard_utr`, n = 12 — reported, not concluded

| Arm | Pre-registered | Any far-sized non-near person |
|---|---|---|
| control, full frame @1280 | 0/12 | 0/12 |
| crop192 @640 (yolo11m / yolo11x) | 1/12 | 5/12 |
| every other arm | 0/12 | 1–3/12 |

Same direction, same mechanism, but the population is 12 contacts of which several
are anchored on a stationary ball. **Underpowered. Do not quote a rate from it.**

---

## What this does NOT show

**A pass here proves the crop FINDS the player. It does not prove a phone can afford
it.** That needs P0-0 and a device; no phone benchmark exists in this repo.

The on-device shape this implies, and its cost:

- **One FIXED-SIZE crop per contact, batched.** Core ML dislikes dynamic input
  shapes; a variable-shape graph pushes the work off the ANE onto the CPU and the
  saving evaporates. Fixed 192×192 crops resized to a fixed 640×640 tensor is a
  legal enumerated-shape graph. A per-contact crop whose size varies is not.
- The arithmetic that makes it interesting: a 640² tensor is **4× cheaper** than the
  1280² full-frame pass, and it runs **once per contact** (order 10² per match)
  rather than on every pose frame (order 10³–10⁴). That is the affordability
  argument, and it is arithmetic, not a measurement.
- It buys the far player only. The near player is already found by any arm and
  needs no crop.

## Reproduce

```bash
./backend/.venv-train/Scripts/python.exe tools/p0_3_crop_probe.py \
    --match data/output/p0_1280_yt_match40.json \
    --video data/incoming/Hardcourt/yt_match40.mp4 \
    --keypoints data/yt_match40_pts.json \
    --out data/output/p0_3_probe_yt_match40.json \
    --sheet-prefix data/output/p0_3_sheet_yt_match40 --device cuda
./backend/.venv-train/Scripts/python.exe tools/p0_3_tolerance_sweep.py \
    --probe data/output/p0_3_probe_*.json --out data/output/p0_3_tolerance_sweep.json
```

Artifacts, all provenance-stamped (model + sha256, device, seed, git commit,
calibration file + sha256, resolved imgsz per arm — read from the RESOLVED
estimator, not a preset table):

- `data/output/p0_3_probe_yt_match40.json`, `..._am_hard_utr.json`,
  `..._yt_match40_mechanism.json`
- `data/output/p0_3_tolerance_sweep.json`, `data/output/p0_3_mechanism_sweep.json`
- **Contact sheets, one per crop arm per clip:**
  `data/output/p0_3_sheet_{clip}_crop{C}at{S}_{m,x}.png`.
  The two that matter for review are
  `p0_3_sheet_yt_match40_crop192at640_x.png` (25 tiles) and
  `p0_3_sheet_am_hard_utr_crop192at640_x.png` (12 tiles).
  Magenta = the ball at contact; **green** = control ACCEPTED, orange = control
  rejected; **cyan** = crop ACCEPTED, red = crop rejected; white = the crop region.
  Each tile is rendered at that arm's own crop scale — a 25 px player inside a 448
  tile shrunk to fit is unreadable, and an unreadable contact sheet is how the first
  P0-3 number survived.
- Population sheets: `data/output/p0_3_pop_far_yt_match40.png`,
  `data/output/p0_3_pop_{clip}.json`.

## What a reviewer should check on the sheets

1. Is the magenta cross on a **far-end contact** (a far player striking), or on the
   near player, or on a ball lying on the court? Count them.
2. Are the **red/cyan crop boxes on the far PLAYER**, or on a fence post, a bag, a
   spectator? Median box height is 32 px, so this needs the zoomed sheet.
3. Do any **green** boxes appear at all? There should be none — the claim is that
   the full frame finds nothing.
