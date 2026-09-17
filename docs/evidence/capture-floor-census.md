# P3 — does ANY footage we own meet the v1 capture floor?

**Measured 2026-09-12 by the lead** (`ffprobe` over file properties — no model, no tuning, so it
cost no agent slot while P1 held the one child). **What every number here was measured against:**
the container metadata of the files themselves, read with `ffprobe`, plus — for the mount-fixity
leg — the already-published ORB/RANSAC background-displacement table in
[clip-shot-map.md](clip-shot-map.md). Nothing here is a model output and nothing was scored
against a model.

**Why it exists.** SPEC §2 made **60 fps AND 1080p HARD floors** on 2026-09-11. The corpus was
assembled over the preceding months under a 30 fps, 720p-tolerant regime. Nobody had checked
whether the footage and the spec are compatible, and it is the item most likely to silently block
everything downstream: every other v1 measurement is scored on this footage.

**BAR, pre-registered by the founder before the run** (recorded in `.claude/journals/lead.md`
with three specification calls made *before* ffprobe ran): if fewer than **5 compliant clips
spanning at least 3 surfaces** exist, record that the v1 validation corpus **DOES NOT EXIST** and
P5 (the capture protocol) goes to the top of the queue.

---

## VERDICT: THE BAR FIRES. The v1 validation corpus does not exist.

It fails on the **surface-span** leg, not the clip-count leg, and it fails under both readings of
the frame-rate floor:

| Reading | Compliant clips | Surfaces spanned | Bar needs | Verdict |
|---|---|---|---|---|
| **STRICT (>= 60.0 fps)** — the graded one | **7** (1.3 h) | **2** — Clay 1, Hardcourt 6 | >=5 clips AND >=3 surfaces | **FAIL** |
| Tolerant (>= 59.9 fps, admits NTSC 59.94) | 14 (2.5 h) | **2** — Clay 2, Hardcourt 12 | >=5 clips AND >=3 surfaces | **FAIL** |

**Shell: 0 compliant. Grass: 0 compliant.** Those are two of the three surfaces §7's split
requires, and neither contributes a single clip.

## The 59.94 question was pre-registered, and it mattered

It **doubles the clip count** (7 -> 14), which is exactly why the call was written down before the
probe ran rather than after. SPEC §2 says "60 fps minimum, HARD"; NTSC 59.94 (60000/1001) is
*below* 60.0, so **the bar is graded strictly** and the tolerant number is reported beside it for
the founder to rule on. **It changes no verdict**: the surface count is 2 either way.

`r_frame_rate` and `avg_frame_rate` were both read so a container quirk could not silently resolve
a disagreement. **They disagree by >0.5 fps on zero of 213 clips**, so the rate is unambiguous.

## THE FINDING THAT MATTERS MORE THAN THE HEADLINE: resolution and frame rate are ANTI-CORRELATED here

| | 30 fps | 59.94 fps | 60 fps |
|---|---|---|---|
| **2160 height (4K)** | **58** | 0 | 0 |
| 1080 height | 4 | 7 | 7 |

**Every one of the 58 4K clips is 30 fps, and every 60-ish fps clip is exactly 1080p. Not one clip
in the corpus is both.** The high-resolution footage *is* the Shell footage — 58 of the 64 shell
clips are 3840x2160 at 30 fps — so the surface with the best pixels is disqualified by frame rate,
and the surface that clears frame rate has no headroom above the resolution floor.

This is not a coincidence to be worked around. It is two different acquisition regimes: the shell
recordings are 4K/30 phone captures, and the 60 fps material is broadcast-style tournament footage.

### Full cross-tab, canonical 116 clips

| Surface | 24 | 25 | 29 | 29.97 | 30 | 50 | 59.94 | 60 | total |
|---|---|---|---|---|---|---|---|---|---|
| Clay | 3 | 1 | 0 | 1 | 1 | 0 | 2 | 1 | 9 |
| Grass | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 4 |
| Hardcourt | 0 | 4 | 2 | 5 | 6 | 1 | 7 | 14 | 39 |
| Shell | 0 | 0 | 0 | 1 | 61 | 0 | 0 | 2 | 64 |

Grass's two 60 fps clips are 720p; Shell's two are 360p/720p. Both fail the resolution floor —
which is why 19 clips clear 60.0 fps but only 7 clear both floors.

**Scope note:** 213 video files exist under `data/incoming/`; 14 are in `Raw - Do Not Process`
(skipped by rule — sweeping it counts the same court twice) and **83 are per-point splits in
`Hardcourt/hc*_N/` subdirectories that the canonical 116 count does not include.** All 83 are
30 fps/1080p, so **including them changes no number in this census** — the compliant set is
identical at 7 strict / 14 tolerant whether the scope is the canonical 116 or all 199 non-Raw
clips. Counted both ways for exactly that reason.

## THE THIRD FLOOR IS THE BINDING ONE, AND IT IS NOT FRAME RATE

SPEC §2's floor has three legs: 60 fps, 1080p, **and a fence-mount or tripod** ("handheld is
explicitly out of scope"). Mount fixity is **not an ffprobe-able property** and was not guessed
here. But it does not need to be guessed — it is **already measured** for 5 of the 14 compliant
clips, in [clip-shot-map.md](clip-shot-map.md)'s background-displacement table.

Read against the two clips in this repo that are *known* static shell tripods:

| Clip | Compliant? | Max background displacement (px@640) | Max zoom | What it is |
|---|---|---|---|---|
| `flexi_joy_p01` | no (4K/30) | **0.4** | — | **known static tripod — the reference** |
| `hillsborough_p02` | no (4K/30) | **0.1** | — | **known static tripod — the reference** |
| `sAjkpeRq4P4` | yes (59.94) | 6.3 (median 2.7) | 0.2% | near-fixed |
| `uR5q2cSM6AY` | yes (60.0) | 20.5 (median 19.2) | 0.6% | slow drift |
| `UHf0LeMU2pg` | yes (60.0) | 28.2 (median 25.9) | 1.1% | drift |
| `CYqapSq5llo` | yes (60.0) | 38.1 (**median 3.8**) | 2.9% | fixed but for one outlier frame |
| `A7vXlWIlyrI` | yes (60.0) | **188.3** | **40%** | **broadcast pan-and-zoom — out** |
| `HoHxFSX_gLk_s1 / s2 / s3` | yes (59.94) | 189.5 / 105.9 / 138.5 | — | **camera moves — out** |

**A genuine tripod reads 0.1-0.4 px. The best compliant clip reads 6.3 px — sixteen times the
worst static reference.** Four of the 14 compliant clips are eliminated outright
(`A7vXlWIlyrI` plus the three `HoHxFSX_gLk_*`), and **9 of the 14 have no fixity measurement at
all.**

**TWO HONEST LIMITS ON READING THAT TABLE, because it would be easy to overclaim:**
1. **These displacements are measured across frames sampled over the WHOLE clip** (5%-95%), so
   6.3 px on a 1756 s clip is slow drift, not per-frame jitter. SPEC §1's drift detector tolerates
   **15 px sustained over 3 frames**, which is a per-frame criterion — `sAjkpeRq4P4` and
   `CYqapSq5llo` would pass it comfortably. Clip-scale drift and frame-scale stability are
   different quantities and this table bounds only the first.
2. **No new threshold is being set here.** The 0.1-0.4 px static references and the 6.3-188.3 px
   compliant clips are both pre-existing published measurements; putting them in one table is a
   comparison, not a gate. Nothing in this census invents a fixity bar.

## What the compliant footage actually is — and why it tests the wrong camera

Every clip that clears both floors is broadcast-style tournament footage on an elevated mount.
**The one amateur fixed-mount clip in the compliant set is `am_hard_utr`** — and it is 59.94 fps
(fails the strict reading) on a **1.74 m** mount. This project's own height curve
([camera-height-curve.md](camera-height-curve.md)) runs from **3.81 m** bounce error at a 1.0 m
mount to **0.37 m** at 8 m, so 1.74 m sits near the bad end of it — orders of magnitude from the
10 cm bar, and `am_hard_utr` is separately recorded as measurable to only **7.5 m of 23.8 m** of
court depth. Five of the 14 are BALL
gold clips, which is fine for validation (they are test-only by rule) but says nothing about mount.

**So the corpus has no clip that is simultaneously >=60 fps, >=1080p, fixed-mount, AND at a mount
height where 10 cm is physically reachable.** The floor that binds is not frame rate and not
resolution — it is that we own no spec-compliant *camera setup*, on any surface.

## ADDENDUM 2026-09-15 — which clip is CLOSEST, and a nuance P1 changed

The headline above is "no clip is simultaneously >=60 fps, >=1080p, fixed-mount AND at a height
where 10 cm is reachable". That remains true, but **P1 changed why the last clause is true, and the
original emphasis was misleading.** This census implied the height problem was our *low* mounts.
P1 then measured that **no mount height reaches 10 cm at realistic noise** — 3.0 m gives 6.1%, and
even perfect pixels give only 71.7%. So the height clause is now trivially satisfied by every clip,
and **the leg that actually disqualifies our compliant clips is FIXITY.**

Cross-referencing the census against the committed calibrations and their `_audit` camera heights:

| Clip | Surface | fps | Resolution | Fitted camera | Audit | Background drift |
|---|---|---|---|---|---|---|
| **`sAjkpeRq4P4`** | **Clay** | 59.94 | 1920x1080 | **3.33 m** | PASS | **6.3 px** — best in the corpus |
| `UHf0LeMU2pg` | Hardcourt | 60.00 | 1920x1080 | 3.35 m | PASS | 28.2 px |
| `uR5q2cSM6AY` | Hardcourt | 60.00 | 1920x1080 | 3.32 m | PASS | 20.5 px |
| `L73ep7JHiJ4` | Hardcourt | 59.94 | 1920x1080 | 2.89 m | PASS | not measured |
| `tc8CGFxyRE8` | Hardcourt | 59.94 | 1920x1080 | 2.00 m | PASS | not measured |

**`sAjkpeRq4P4` is the single closest clip we own** — Clay, 1080p, a 3.33 m fitted camera, a PASS
audit, and by far the tightest background drift at 6.3 px (against 0.1-0.4 px for a known tripod).
Its only hard failure is **59.94 fps against a strict 60.0 floor**, which is the NTSC question this
census pre-registered and left for the founder.

**That does not soften the verdict** — the bar failed on the surface leg (2 of 3 required), and one
clip on one surface is not a validation corpus. But "we have nothing usable at all" would overstate
it, and both P2 and P5 need to know which clips are worth pointing at.

**For P2 specifically:** only **three** files in the whole corpus have a perception cache —
`am_hard_utr` (1.74 m), `demo30` (1.38 m) and `yt_match40` (1.64 m), all LOW-CAMERA. **CORRECTED
2026-09-16 (qa, P2): that is TWO recordings, not three.** `demo30` is `yt_match40` frames
2552-3421, and `data/output/demo30.perception.json` was not computed from `demo30.mp4` (1,108
entries for 870 frames; `demo30.json` names `yt_rally2.mp4`). **The same static camera is
calibrated at 1.38 m in one file and 1.64 m in the other** — a 0.26 m disagreement that P8 (court
mapping) should explain. Running
perception on a fresh clip costs 0.7-1.1 s/frame, so an occlusion census built on cached clips is
cheap and one built on the compliant clips is not.

## Consequences

1. **P5 (the capture protocol) goes to the top of the queue**, per the bar. A court visit is the
   only route to a v1 validation corpus, and it has days of lead time.
2. **This strengthens P5's existing argument rather than adding a new one.** P5 already said the
   10 cm gold set is not labellable from the footage we own. This says something stricter: the
   footage does not even meet the *capture* floor, so the gap is not a labelling gap.
3. **P4(iii) is narrowed, not contradicted.** The shell blocker is still void for v1 — a manual
   four-tap works on a shell, and ten shell calibrations prove it. But **all 58 4K shell clips are
   30 fps**, so shell is unblocked for *court* work and remains unusable for *bounce* work, which
   SPEC §2 forbids attempting below 60 fps. The court visit must cover shell if §7's surface split
   is to be met.
4. **Nothing here blocks P1.** P1 runs on synthetic flights through a real calibration and needs no
   compliant clip.

**Raw census:** `data/output/capture_floor_census.json` (213 clips, 0 probe errors).
