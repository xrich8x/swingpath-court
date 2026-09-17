# Near baseline + net line — how precisely are they actually detected?

> DELIVERABLE for the falsifier named in
> [net-baseline-solve-without-far-line.md](net-baseline-solve-without-far-line.md):
> *"what is the detection precision of the near baseline and the net line specifically?"*
> Run by **backend-dev**, 2026-09-06. Bar pre-registered in
> `.claude/journals/backend-dev.md` **before** any measurement.
>
> Harness: `eval/near_line_precision.py`. Results: `data/output/near_line_precision.json`.
> Population: **all 40 clips** with human-clicked doubles corners that
> `eval/score_truth.truth_sources` yields (20 court-gold + 20 reference). Nothing dropped.

# VERDICT: THE ≤2 px PREMISE FAILS.

One of the four observables meets it. Three do not, and two miss it by an order of
magnitude. **The end-to-end extrapolated far baseline lands 17.4 px@640 from the human far
corners against the shipped 8.1 px bar**, and it is available on only **10 of 40** clips.

**But the geometry itself is vindicated, on real cameras, not just synthetically.** Fed the
**truth** observables from the human clicks, the solve reproduces the human far baseline row
to a **median 0.007 px@640, worst 0.75 px, on all 40 clips.** The model is not the limit.
Detection is — and specifically the two **widths**, not the two rows.

| § | Ask | Status |
|---|---|---|
| 1 | The shared protocol (published for qa) | done |
| 2 | Pre-registered bar | done |
| 3 | The four observables, per clip and pooled | done |
| 4 | End-to-end: the extrapolated far baseline on real clips | done |
| 5 | Verdict, and what actually breaks | done |
| 6 | Exchange with qa | **BLOCKED — `SendMessage` is disabled this session** |

---

## 1. THE SHARED PROTOCOL

qa is measuring whether temporal integration (the clean plate) sharpens **these same two
lines**. Its number is only comparable to mine if we measure the same way, so the protocol is
fixed here. **backend-dev measures on the SINGLE FRAME; qa measures the identical quantities
on the CLEAN PLATE.** One variable: plate vs frame.

**Units.** Everything in **px@640** — frame resized to width 640, detections and truth both in
that space. Not cosmetic: the shipped **8.1 px** reconstruction bar and the **6.4 px** line
floor are both px@640, so the Monte Carlo's **≤2 px** premise is px@640 too. A number quoted
at native 1280/1920/3840 width is 2–6× the same error and is **not** comparable.

**Truth.** The human-clicked four doubles corners in `data/<clip>_pts.json` and the court-gold
per-frame clicks (never edited — rule 9). Homography from those four points; then project:

| observable | court-metre construction |
|---|---|
| near baseline row `r_near` | mean row of the projected near corners, `(0, 0)` and `(10.97, 0)` |
| net line row `r_net` | mean row of the projected **net GROUND** points, `(0, 11.885)`, `(10.97, 11.885)` |
| near baseline width `w_near` | horizontal separation of the projected near corners |
| width at the net `w_net` | horizontal separation of the projected net-line/doubles-sideline points |

**Detection.** The **shipped** detector, unchanged: `calibration.court_line_mask(frame)` →
`courtfit._detect_lines(mask, w)`, which returns distinct infinite lines `(theta, rho, weight)`
after merging Hough segments of the same painted line. No new detector was built.

**Matching.** For each of four model lines — near baseline, net ground line, left doubles
sideline, right doubles sideline — take the **projected truth line** and select the detected
line with the smallest **mean perpendicular distance at the truth segment's two endpoints**,
angle tolerance ≤6°, gate 12 px@640. Truth-seeded on purpose: this measures **localisation,
not search**, which is the only thing the solve's premise depends on.

**A line that does not match is a MISS**, reported, never a population filter (rule 10).

**Detected observables** come from intersecting the detected across-line with the two detected
sidelines — the same construction a real implementation would use.

**The net-line caveat.** *There is no painted line at the net.* The solve needs the net
**GROUND** row (`y = 11.885`); what is physically detectable is the net **TAPE** (0.914 m at
centre, 1.07 m at the posts) or the net's base. Both are measured below; §5 prices the
confusion.

## 2. THE PRE-REGISTERED BAR

Written to the journal before measuring; not restated more kindly here.

- **PASS** — pooled median ≤ **2.0 px@640** on **all four** observables, **and** the end-to-end
  extrapolated far-baseline error on real clips ≤ **8.1 px@640** at the median.
- **FAIL** — any one of the four at ≥ **6.4 px@640** pooled median, **or** end-to-end median
  > 8.1 px@640, **or** the net line missed on > 50% of clips.
- **BORDERLINE** — in between. Not rounded to PASS.

## 3. THE FOUR OBSERVABLES

### 3.1 Pooled — reported separately, because the geometry is not equally sensitive to them

| observable | n with a value | **median px@640** | p90 | max | vs the 2.0 px premise |
|---|---|---|---|---|---|
| **(a) near baseline ROW** | 16 | **0.83** | 3.60 | 8.33 | **meets it** |
| **(b) net line ROW** | 11 | **6.22** | 9.93 | 11.54 | **3× over** |
| **(c) near baseline WIDTH** | 16 | **12.44** | 43.22 | 62.84 | **6× over** |
| **(d) WIDTH at the net** | 11 | **44.63** | 71.12 | 105.16 | **22× over** |

The two **rows** are the good half; the two **widths** are the failure, and the width ratio is
what the solve is most sensitive to. A pooled single figure would have hidden exactly that.

### 3.2 Availability comes first — how often each line is found at all

Precision is only meaningful where the line is found. Match rate, protocol matcher, 40 clips:

| model line | matched | median perp px@640 | p90 | max |
|---|---|---|---|---|
| near baseline | **36/40** | 2.60 | 7.18 | 11.86 |
| net GROUND line | **24/40** | 5.80 | 10.23 | 11.57 |
| left doubles sideline | **38/40** | 2.03 | 4.33 | 9.25 |
| **right doubles sideline** | **18/40** | 1.54 | 9.87 | 11.82 |
| (far baseline, for reference) | 38/40 | 2.53 | 5.01 | 8.54 |

Two things follow. First, the **right sideline — not the net — is the binding availability
constraint** at 18/40; all four observables exist together on only **10 of 40 clips (25%)**.
Second, the medians are **censored by the 12 px gate**: a line that is really 20 px out is
scored as a MISS, so the quoted medians are optimistic by construction, not pessimistic.

### 3.3 Per clip — every clip, misses included

`NB line` / `net-GROUND line` / `L side` / `R side` are perpendicular line-to-truth distances;
the last five columns are the four observables and the end-to-end far-baseline row.

| clip | src | native w | NB line | net-GROUND line | L side | R side | (a) NB row | (b) net row | (c) NB width | (d) net width | far row |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `am_beginner` | gold | 640 | 3.15 | 5.73 | 1.08 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_classB` | gold | 640 | 2.98 | 8.76 | 2.94 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_college` | gold | 640 | 5.24 | 4.51 | 1.97 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_fr_sud` | gold | 640 | 4.50 | MISS | 4.24 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_grass1` | gold | 640 | 2.50 | MISS | 2.51 | 4.56 | 1.53 | MISS | 38.5 | MISS | MISS |
| `am_indoor_hard1` | gold | 640 | 10.31 | MISS | 8.55 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_indoor_hard2` | gold | 640 | 0.89 | 10.44 | 1.47 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_lk35` | gold | 640 | 7.94 | 4.45 | 1.26 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_ntrp30` | gold | 640 | 2.28 | MISS | 2.55 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_ntrp40` | gold | 640 | 2.97 | 9.40 | 2.29 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_ntrp45_courtlevel` | gold | 640 | 4.32 | MISS | 2.11 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_ntrp45w` | gold | 640 | MISS | 6.57 | 3.19 | 9.74 | MISS | 5.83 | MISS | 44.6 | MISS |
| `am_ntrp50` | gold | 640 | 7.13 | 7.89 | 1.84 | 4.60 | 8.33 | 7.86 | 62.8 | 59.0 | 3.79 |
| `am_rally32short` | gold | 640 | 1.00 | 5.86 | 2.51 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_rec30` | gold | 640 | 2.94 | MISS | 2.37 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_usta40` | gold | 640 | 3.08 | 11.57 | 2.03 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_usta45` | gold | 640 | 1.45 | MISS | 2.11 | 1.80 | 1.05 | MISS | 11.4 | MISS | MISS |
| `am_usta45final` | gold | 640 | 1.85 | MISS | 3.90 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_usta60` | gold | 640 | 3.64 | MISS | 2.03 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_wingfield_clay` | gold | 640 | MISS | 2.01 | 1.39 | MISS | MISS | MISS | MISS | MISS | MISS |
| `A7vXlWIlyrI` | ref | 1920 | 2.23 | 9.74 | 0.79 | 11.82 | 2.24 | 9.93 | 20.6 | 105.2 | 4.29 |
| `CYqapSq5llo` | ref | 1920 | 11.86 | 1.94 | MISS | MISS | MISS | MISS | MISS | MISS | MISS |
| `HoHxFSX_gLk_s1` | ref | 1920 | MISS | 2.30 | MISS | 4.57 | MISS | MISS | MISS | MISS | MISS |
| `HoHxFSX_gLk_s2` | ref | 1920 | 4.96 | MISS | 0.85 | 1.20 | 4.96 | MISS | 47.9 | MISS | MISS |
| `UHf0LeMU2pg` | ref | 1920 | MISS | MISS | 9.25 | MISS | MISS | MISS | MISS | MISS | MISS |
| `am_hard_utr` | ref | 1920 | 7.24 | MISS | 0.29 | 0.53 | 0.23 | MISS | 1.7 | MISS | MISS |
| `e8T34KoJzOw_s2` | ref | 1920 | 1.35 | MISS | 1.26 | 1.56 | 1.21 | MISS | 0.5 | MISS | MISS |
| `flexi_franz_p01` | ref | 3840 | 1.53 | MISS | 0.59 | MISS | MISS | MISS | MISS | MISS | MISS |
| `flexi_franz_p07` | ref | 3840 | 1.64 | 2.29 | 0.81 | MISS | MISS | MISS | MISS | MISS | MISS |
| `flexi_joy_p01` | ref | 3840 | 0.43 | 5.74 | 0.72 | 1.23 | 0.16 | 5.21 | 7.4 | 34.1 | 4.18 |
| `flexi_joy_p07` | ref | 3840 | 0.81 | 8.38 | 4.80 | 1.43 | 0.19 | 8.38 | 36.5 | 47.1 | 6.63 |
| `hillsborough_p02` | ref | 3840 | 0.89 | 4.83 | 0.45 | 0.98 | 0.89 | 4.77 | 8.5 | 39.0 | 3.22 |
| `hillsborough_p08` | ref | 3840 | 1.69 | 5.49 | 0.70 | 0.77 | 0.22 | 5.12 | 6.4 | 33.2 | 3.78 |
| `mpc_mixed_p02` | ref | 3840 | 2.16 | 11.54 | 2.40 | 1.52 | 0.42 | 11.54 | 12.7 | 71.1 | 8.01 |
| `mpc_mixed_p08` | ref | 3840 | 1.85 | 3.23 | 2.90 | 0.17 | 0.77 | 3.23 | 29.0 | 17.6 | 2.13 |
| `mpc_tuesday_p01` | ref | 3840 | 1.05 | 8.21 | 1.04 | 10.15 | 0.09 | 6.22 | 37.1 | 54.9 | 3.22 |
| `mpc_tuesday_p07` | ref | 3840 | 2.71 | MISS | 0.98 | 0.40 | 1.22 | MISS | 8.7 | MISS | MISS |
| `sAjkpeRq4P4` | ref | 1920 | 4.83 | 3.57 | 1.78 | MISS | MISS | MISS | MISS | MISS | MISS |
| `tc8CGFxyRE8` | ref | 1920 | 4.79 | 7.75 | 2.34 | 1.68 | 0.62 | 7.55 | 12.2 | 41.2 | 5.14 |
| `uR5q2cSM6AY` | ref | 1920 | 1.39 | MISS | 4.54 | MISS | MISS | MISS | MISS | MISS | MISS |

An **observation, not a claim** (source and native resolution are confounded): the near
baseline is located far better on the 3840-wide references (0.4–2.7 px@640) than on the
640-wide gold frames (0.9–10.3 px@640). If that survives an isolated test, input resolution
is a lever on the *one* observable that currently passes.

### 3.4 The net GROUND line does not exist as paint — and the TAPE is not a substitute

| | found within 12 px@640 | median perp |
|---|---|---|
| net **GROUND** line (what the solve needs) | **24/40** | 5.80 |
| net **TAPE** (`(x, 11.885, 1.07)`, projected in 3D) | **38/40** | 4.10 |

The tape is **more findable and better localised** than the ground line — as expected, since
one is a real white object and the other is an imaginary line under the net. The two rows sit
a median **25.2 px@640 apart** (range 15.5–47.4) on this corpus.

**Price of substituting one for the other:** feed the solve the tape row in place of the ground
row, with otherwise perfect (truth) widths, and the extrapolated far baseline lands a median
**32 px@640** out (min 19, max 59) — about **4× the shipped bar**, on every clip. This is the
same confusion that already condemned a correct calibration in
[net-tape-camera-height-consistency.md](net-tape-camera-height-consistency.md).

## 4. END-TO-END — where the extrapolated far baseline actually lands

Better evidence than the Monte Carlo, because it uses this project's real cameras.

### 4.1 The control first — is the model or the detection at fault?

Fed the four **truth** observables from the human clicks:

| | n | median | p90 | max |
|---|---|---|---|---|
| **far baseline ROW error, solve from TRUTH observables** | **40** | **0.007 px@640** | 0.06 | **0.75** |

The four-observable solve reproduces the human far baseline essentially exactly on **every**
real clip, including 1.38–2.9 m mounts and 640–3840 px widths. Lens distortion, roll and an
off-centre principal point do **not** break it at this level. **Everything below is detection
error, not model error.**

### 4.2 From the DETECTED observables — the 10 clips where all four lines are found

| quantity | n | median px@640 | p90 | max |
|---|---|---|---|---|
| far baseline **ROW** error | 10 | **3.99** | 6.77 | 8.01 |
| far baseline **WIDTH** error | 10 | **32.7** | 50.7 | 69.1 |
| **far CORNER error** (`hypot(row, width/2)`) | 10 | **17.4** | — | — |

**The row alone would have passed. The corner does not, and the corner is the shipped metric**
— the 8.1 px bar is a reconstruction error on the court corners, not on a single row. Reporting
only the row error here would have been the kind number, and it would have been wrong.

### 4.3 Why the row survives and the width does not — the mechanism

Two anchor rows pin the solve exactly, so the far row follows from a **cross-ratio identity**:

```
r_net − r_far = (r_near − r_net) · D / (D + 23.77)
```

`D/(D + 23.77)` is ≈ 0.11–0.25 for the standoffs on this corpus and is **compressive** — a 20%
error in the width ratio `k` (and hence in `D`) moves the far row by only a few px, because the
dominant term `(r_near − r_net)` is *directly observed*. Measured: median `k` error **19.6%**,
median far-row error **4.0 px@640**.

The far **width** has no such protection: `w_far = f·W/(D + 23.77)` inherits the `D` error
close to in full. Measured `D`: e.g. `A7vXlWIlyrI` 5.90 m true → 2.71 m recovered;
`mpc_mixed_p02` 6.21 → 3.40. Far width errors of 25–50%.

I checked and reject the tempting explanation that the two width errors cancel in the ratio:
median `k` error (19.6%) is **as large as** the worst single width error (17.5%). There is no
cancellation. The row is protected by the cross-ratio, not by correlated noise.

### 4.4 One robust by-product worth keeping

**Camera HEIGHT survives a 40% standoff error.** From the detected observables: 1.64→1.62,
1.64→1.61, 2.11→1.95, 1.69→1.67, 2.88→2.92, 2.01→1.99 m. Worst 0.16 m, typical 0.02–0.05 m.
If a use is wanted for this solve, **estimating mount height from the near baseline and net —
without the far line — is the part that works**, and that feeds the setup criterion
([live-setup-criterion.md](live-setup-criterion.md),
[net-tape-clearance](net-tape-camera-height-consistency.md)) rather than the calibration.

## 5. VERDICT

**FAIL, against the bar as written.** Triggered twice over:

1. **(c) 12.44 and (d) 44.63 px@640** pooled medians, both ≥ the 6.4 px FAIL clause. (b) at
   6.22 is a hair under it and is still 3× the premise.
2. **End-to-end far corner 17.4 px@640** against the 8.1 px bar.

The third FAIL clause — net line missed on >50% — is **not** triggered (24/40 found), but the
**right sideline is** effectively the equivalent problem at 18/40, and all four observables
coexist on only 10/40 clips.

**Plainly: the ≤2 px premise does not hold.** It holds for exactly one of the four observables,
the near baseline row (0.83 px@640). The premise's *reasoning* — "close to the camera,
therefore well resolved" — is confirmed for **rows** and refuted for **widths**, because a
width is not a row: it is the separation of two intersections with **oblique sidelines**, where
a sub-degree angle error is levered into tens of pixels. That asymmetry was not in the Monte
Carlo, which put i.i.d. gaussian noise on all four observables as if they were the same kind of
measurement.

**What this does not kill.** The geometry is exact on real cameras (§4.1); the far *row* is
recoverable to ~4 px; camera *height* is recoverable to ~0.05 m. The failure is localised and
named: **the width ratio, which needs the two doubles sidelines, which are the least reliably
detected lines in the set.**

### A bug-class finding, reported not fixed

The shipped truth-matcher `eval/corr_attrib.py:_match_line` gates on `|Δrho|` measured from the
**image origin**. For a long oblique line a 6° tilt barely moves rho, so the gate is nearly
inert: it accepted **right-sideline** "matches" sitting **34.9 px@640 median and up to 316
px@640** from the truth segment, on 27 of 40 clips. Under a geometric perpendicular matcher
only 18 of 40 match at all. Any population or per-line residual built on that matcher for
oblique lines is looser than it reads. Recorded here; not changed (`corr_attrib` is not this
run's file).

## 6. EXCHANGE WITH QA — BLOCKED

The brief directed me to message `qa` directly. **`SendMessage` is not available:** the tool
call returns *"No such tool available: SendMessage. SendMessage is disabled for this session,
in subagents as well as here."* The protocol was therefore published here, in §1, before the
sweep was run, as the only channel available; §3 and §4 are the promised baseline numbers.

**What qa needs from this file to make its clean-plate number comparable**, in one place:

- Measure in **px@640**. Single frame is the baseline; the plate is the treatment.
- The comparison lines and their single-frame baselines: **near baseline 2.60 px@640 median,
  36/40 found**; **net GROUND line 5.80 px@640 median, 24/40 found**; left sideline 2.03, 38/40;
  **right sideline 1.54 but only 18/40 found**.
- **The most useful thing the plate could move is not precision on the near baseline — it is
  availability of the RIGHT SIDELINE (18/40) and of the net GROUND line (24/40).** Those two,
  not the near baseline, are what stop the solve running on 30 of 40 clips.
- Beware the same trap: report the four observables separately, and if reporting an end-to-end
  number report the **corner**, not the row.

If qa returns a sharpening factor, §4.2 re-runs directly from
`data/output/near_line_precision.json` via `eval/near_line_precision.py`.

## NOT ESTABLISHED THIS RUN

- **qa's clean-plate arm** — blocked on messaging; not attempted here (it is qa's file).
- **Whether input resolution is a real lever** on the near baseline (§3.3 is confounded).
- **Whether the widths are recoverable from a better sideline treatment** (e.g. vanishing-point
  constrained fitting of the two sidelines rather than independent Hough lines). This is the one
  branch the mechanism in §4.3 actually points at, and it was not run.
- Multi-frame behaviour: this is `--frames 1`, one frame per clip.
