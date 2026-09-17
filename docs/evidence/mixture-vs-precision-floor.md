# Mixture vs precision floor — the §4.1 falsifier, run

> **qa, 2026-09-09. COURT ONLY. Verification only — I changed nothing.** This runs the bar
> pre-registered by researcher in `docs/evidence/court-recall-what-would-actually-move-it.md`
> §4.1, copied verbatim and not adjusted. **Measured against nothing external**: this is a
> shape-of-distribution question about fits disagreeing with each other. **It is not accuracy
> and must never be quoted as accuracy.**

## VERDICT: INDETERMINATE

**Neither reading reaches its bar, on either population.**

| population | measurable clips | MIXTURE | PRECISION FLOOR | INDETERMINATE | bar |
|---|---:|---:|---:|---:|---|
| strict-16 (primary) | 11 | **4** | **1** | 6 | ≥6 of ~12 either way |
| excluded-4 (reported separately) | 4 | 1 | 0 | 3 | — |
| pooled 20 (the run-4 pool) | 15 | 5 | 1 | 9 | — |

The bar says "anything else: INDETERMINATE, and it stays indeterminate; the bands do not move
after the fact." So: **INDETERMINATE.** I am not rounding it toward either reading.

**The kill condition did not fire.** This run does **not** establish PRECISION FLOOR, so it does
**not** close researcher's part (a) — and it does not confirm it either. The direction stays open
on this evidence, which is the least useful of the three possible outcomes and is what happened.

**The two things that matter more than the headline:**

1. **On the four clips that motivated the whole question — the static 4K shell tripods at
   29.9 / 31.9 / 36.3 / 37.5 px@640 — the test is at or past the edge of what it can resolve.**
   One (`flexi_joy_p01`) is UNMEASURABLE by the bar's own ≥3-locked-frames rule; its 29.9 px
   figure is **a single pair of frames**. Two more rest on **3 pairs each**. Not one of the four
   returns MIXTURE.
2. **Every MIXTURE verdict in the pool is a 1920-wide clip. Zero of the six measurable 3840-wide
   shell clips returns MIXTURE.** The mixture evidence comes entirely from a different resolution
   and a different footage type from the observation the reading was invented to explain.

---

## 1. What was reused and what was recomputed

**The bar's premise — "no new measurement is required, `interframe.json` already stores all
pairwise distances per clip" — is wrong, and I could not honour it.** `interframe.json` stores
per-clip **medians and maxima only** (`D_raw`, `D_comp`, `W_*`); it stores neither the pairwise
matrix nor the quads, and clustering needs the quads.

- **RECOMPUTED (everything the verdict rests on):** every per-frame court quad, by calling
  `courtfit.auto_fit_frame` on the same 8 `run_refs.frame_positions` frames of each clip — the
  same call the vote consumes, in the same 8-frame configuration that produced the motivating
  observation. Script: `scratchpad/modality.py`; raw output `scratchpad/modality.json`
  (per-clip cluster membership and the full pairwise table).
- **REUSED:** nothing numerical enters the verdict. Run 4's `D_raw` medians from
  `interframe.json` are used **only as a reproducibility control** (§2), and run 4's ORB+RANSAC
  background-transform method is re-implemented identically for the compensated view.
- **NOT reused:** `motion.json`, `window_motion.json`, `shot_map.json` — not needed here.

So this is the pre-registered falsifier run on **the same inputs recomputed**, not on quietly
different ones. The one deviation from §4.1's description is that it cost a full decode-and-fit
pass, not minutes of re-reading.

## 2. Instrument control — the recomputation reproduces run 4 exactly

All-pairs median per clip, run 4 (`interframe.json`) vs this run:

| clip | run 4 `D_raw` | run 6 | clip | run 4 | run 6 |
|---|---:|---:|---|---:|---:|
| `A7vXlWIlyrI` | 44.16 | 44.16 | `flexi_joy_p07` | 37.53 | 37.53 |
| `HoHxFSX_gLk_s2` | 41.64 | 41.64 | `hillsborough_p02` | 31.86 | 31.86 |
| `CYqapSq5llo` | 32.50 | 32.50 | `hillsborough_p08` | 36.26 | 36.26 |
| `flexi_franz_p01` | 9.15 | 9.15 | `flexi_franz_p07` | 20.80 | 20.80 |

Identical to 2 dp on every clip: the per-frame fit is deterministic and this is the same
quantity, recomputed rather than re-derived.

## 3. Population, stated so the two do not mix

`eval/run_refs.py` was cut **20 → 16** today (`EXCLUDED_CLIPS`, founder ruling,
`docs/evidence/pool-strict-16.md`). I ran all 20 — the run-4 pool, i.e. the clips for which
per-frame fits already existed — with each row flagged, and I report the strict-16 as the
**primary** verdict and the 4 excluded clips **separately**. The verdict is INDETERMINATE on
both, so the pool cut does not change the outcome.

Excluded from the primary count (still measured, shown below): `A7vXlWIlyrI`,
`HoHxFSX_gLk_s1`, `HoHxFSX_gLk_s2`, `UHf0LeMU2pg`. **All 10 shell references are untouched by
the cut**, so the shell half of this test is unaffected.

**UNMEASURABLE (< 3 locked frames — the bar's own rule; named, never counted as agreeing):**
`flexi_joy_p01` (2 locked), `mpc_tuesday_p01` (1), `mpc_mixed_p02` (0), `mpc_mixed_p08` (0),
`mpc_tuesday_p07` (0). Five of the ten shell references cannot enter this test at all.

## 4. Per-clip result — single-linkage at 12 px@640, raw pixels

`within` / `between` are the bar's median within-cluster and median between-cluster pairwise
distances, px@640. `<8 / 8-25 / ≥25` counts pairs by distance, to show the shape.

| clip | s16 | res | locked | k | cluster sizes | within | between | min pair | median | max | <8 / 8-25 / ≥25 | verdict |
|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| `am_hard_utr` | yes | 1920 | 8 | 2 | 7,1 | 5.16 | 14.61 | 2.1 | 6.7 | 19.2 | 16/12/0 | INDETERMINATE |
| `CYqapSq5llo` | yes | 1920 | 8 | 5 | 4,1,1,1,1 | 13.13 | 35.20 | 7.8 | 32.5 | 53.5 | 1/8/19 | INDETERMINATE |
| `e8T34KoJzOw_s2` | yes | 1920 | 8 | 6 | 2,2,1,1,1,1 | 6.26 | 26.02 | 5.8 | 25.6 | 53.3 | 2/11/15 | **MIXTURE** |
| `flexi_franz_p01` | yes | 3840 | 3 | 1 | 3 | 9.15 | — | 7.6 | 9.2 | 16.1 | 1/2/0 | **PRECISION FLOOR** |
| `flexi_franz_p07` | yes | 3840 | 3 | 2 | 2,1 | 5.39 | 21.55 | 5.4 | 20.8 | 22.3 | 1/2/0 | INDETERMINATE |
| `flexi_joy_p07` | yes | 3840 | 5 | 5 | 1,1,1,1,1 | — | 37.53 | 20.1 | 37.5 | 87.1 | 0/3/7 | INDETERMINATE |
| `hillsborough_p02` | yes | 3840 | 3 | 2 | 2,1 | 8.75 | 33.51 | 8.8 | 31.9 | 35.2 | 0/1/2 | INDETERMINATE |
| `hillsborough_p08` | yes | 3840 | 3 | 3 | 1,1,1 | — | 36.26 | 16.4 | 36.3 | 44.8 | 0/1/2 | INDETERMINATE |
| `sAjkpeRq4P4` | yes | 1920 | 8 | 3 | 6,1,1 | 2.53 | 60.39 | 1.4 | 4.5 | 115.5 | 15/0/13 | **MIXTURE** |
| `tc8CGFxyRE8` | yes | 1920 | 7 | 3 | 3,3,1 | 7.19 | 28.93 | 4.1 | 24.2 | 64.7 | 4/7/10 | **MIXTURE** |
| `uR5q2cSM6AY` | yes | 1920 | 8 | 4 | 3,2,2,1 | 2.34 | 31.16 | 1.2 | 27.1 | 61.0 | 5/6/17 | **MIXTURE** |
| `A7vXlWIlyrI` | no | 1920 | 4 | 4 | 1,1,1,1 | — | 44.16 | 21.3 | 44.2 | 62.4 | 0/1/5 | INDETERMINATE |
| `HoHxFSX_gLk_s1` | no | 1920 | 3 | 3 | 1,1,1 | — | 116.49 | 22.5 | 116.5 | 128.2 | 0/1/2 | INDETERMINATE |
| `HoHxFSX_gLk_s2` | no | 1920 | 8 | 5 | 3,2,1,1,1 | 10.25 | 46.66 | 5.6 | 41.6 | 92.5 | 1/10/17 | INDETERMINATE |
| `UHf0LeMU2pg` | no | 1920 | 7 | 6 | 2,1,1,1,1,1 | 4.18 | 52.53 | 4.2 | 51.2 | 98.0 | 1/0/20 | **MIXTURE** |

Motion-compensated clustering (each quad mapped into eval-frame-0's pixel space by an ORB+RANSAC
background similarity, so camera motion cannot manufacture a mode) changes **no clip's verdict**.
It changes `k` on one clip only, `HoHxFSX_gLk_s2` (5 → 2, within 12.91, all-pairs median
41.6 → 15.7), which is already outside the primary population. On every static shell clip
compensation moves the medians by < 0.05 px, as it must.

## 5. The bar has a specification gap. I report it; I did not patch it

**Four clips come back ALL-SINGLETON** — `flexi_joy_p07`, `hillsborough_p08`, `A7vXlWIlyrI`,
`HoHxFSX_gLk_s1`: no two frames within 12 px@640 of each other, so there are **no
within-cluster distances at all** and the within-cluster median is undefined.

Such a clip satisfies neither branch as written: not MIXTURE (needs within ≤ 8), and not
PRECISION FLOOR (needs exactly 1 cluster, or within ≥ 15). By the letter of the bar they are
INDETERMINATE, and that is how they are counted above.

**Clearly labelled as a SECONDARY reading, carrying no part of the verdict:** an all-singleton
result is what a σ ≈ 30 px@640 *scatter* predicts under a 12 px linkage, and it is the opposite
of what repeated modes predict. The nearest pair of fits on those four clips is 20.1 / 16.4 /
21.3 / 22.5 px@640 — a continuous spread with no tight repeats anywhere in it. Read informally,
those four lean toward the precision-floor picture rather than the mixture one. **That reading is
not in the bar and I have not counted it.** The bar's PRECISION-FLOOR branch appears to have been
written expecting a tight scatter to link into one cluster; a scatter wider than the linkage
threshold falls through both branches. **Whoever owns §4.1 should decide what that case means —
before, not after, seeing which clips it would move.**

## 6. Sensitivity — the verdict is not an artefact of the 12 px threshold

Bar threshold is 12 and stays 12. This is a check, not a re-run:

| linkage thr | strict-16 (n=11) MIX / PF / IND | pooled-20 (n=15) MIX / PF / IND |
|---:|---|---|
| 8 | 5 / 0 / 6 | 7 / 0 / 8 |
| 10 | 4 / 1 / 6 | 6 / 1 / 8 |
| **12 (the bar)** | **4 / 1 / 6** | **5 / 1 / 9** |
| 16 | 3 / 2 / 6 | 4 / 2 / 9 |
| 20 | 2 / 6 / 3 | 3 / 6 / 6 |
| 25 | 1 / 9 / 1 | 2 / 11 / 2 |

On the primary population **no threshold from 8 to 16 reaches 6 either way**; the verdict is
INDETERMINATE across the whole plausible neighbourhood of the bar. PRECISION FLOOR only reaches
6 at a 20–25 px linkage, i.e. only by declaring the wrong-court distance itself to be "the same
court" — which would be assuming the answer. The mixture side is nearer to firing on the pooled
20 at a tighter linkage (6 at 10 px, 7 at 8 px) than the precision-floor side ever is at any
threshold at or below the bar. **Neither observation is a verdict, and I am not offering either
as one.**

## 7. The split that is more informative than the headline

| resolution | measurable | verdicts |
|---|---:|---|
| 3840×2160 (shell, static tripods) | 5 | 1 PRECISION FLOOR, 4 INDETERMINATE, **0 MIXTURE** |
| 1920×1080 (broadcast / YouTube / amateur) | 10 | 5 MIXTURE, 5 INDETERMINATE, 0 PRECISION FLOOR |

Every MIXTURE verdict in the pool is 1920-wide. The observation the mixture reading was invented
to explain is 3840-wide. **This test therefore does not license carrying a mixture conclusion
onto the shell clips** — and the shell clips are where the product problem is (0 of 5 recordings
accepted). Note also that 5 of the 10 shell references lock fewer than 3 of 8 frames and drop out
of the test entirely, so the shell half of this population is n=5 measurable clips carrying
3–10 pairs each. **That is underpowered and I am saying so rather than quoting it as a null.**

## 8. Borderline cases a human should look at

- `hillsborough_p02` — within 8.75 vs the bar's ≤ 8.0. **Misses MIXTURE by 0.75 px on 3 pairs.**
  The single most consequential borderline in the run: it is one of the four motivating shell
  clips, and one more clip on the mixture side would still not reach the bar, but it would change
  how the shell column in §7 reads.
- `e8T34KoJzOw_s2` — between 26.02 vs ≥ 25.0. Clears MIXTURE by 1.0 px. **Borderline pass.**
- `flexi_franz_p07` — between 21.55 vs ≥ 25.0. Misses MIXTURE by 3.5 px on 3 pairs.
- `CYqapSq5llo` — within 13.13 vs PRECISION FLOOR's ≥ 15.0. Misses by 1.9 px.
- `HoHxFSX_gLk_s2` — within 10.25; misses MIXTURE by 2.25 px, and is outside the primary pool.
- `flexi_franz_p01` — the **only** PRECISION FLOOR verdict in the run, and it rests on **3 locked
  frames / 3 pairs**. A single-cluster verdict on 3 points is thin evidence and should not be
  quoted alone.

## 9. What this run did NOT do

No corner placement was judged. No `*_pts.json` and nothing in `data/pre_reaudit_backup/` was
read for truth or written. No threshold, constant or shipped default was changed —
`run_refs.EXCLUDED_CLIPS` was cleared **in my process's memory only**, to recover the 20-clip
list, and the repo file is untouched. No `docs/STATE.md` row, no commit, no fix proposed. Nothing
here is scored against human clicks, so no accuracy claim is made or implied — and the
calibration provenance warning `run_refs` now prints applies to any future attempt to do so.

**RAW DATA:** `scratchpad/modality.json` (per-clip cluster membership + the full pairwise table
for all 20 clips), `scratchpad/modality.py`, log `scratchpad/modality.log`, under
`C:\Users\richm\AppData\Local\Temp\claude\E--Claude-Outputs-Cowork-Tasks-Swing-Vision\aad66fbf-cee4-44fd-b9fa-6afd5ab0df01\`.
Scratchpad is session-scoped and will not outlive this session.
