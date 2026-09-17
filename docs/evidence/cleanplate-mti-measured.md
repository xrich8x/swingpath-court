# Clean plate / MTI — does temporal integration sharpen the near-baseline-solve inputs?

> QA verification, 2026-09-06. Coupled to the founder's near-baseline+net-line-only court
> solve (`docs/evidence/net-baseline-solve-without-far-line.md`), which needs the near
> baseline row, the net row, and their two widths detected to **≤2 px** to beat the shipped
> 8.1 px bar. This file asks whether `tools/eval_court_cleanplate.py`'s clean plate + MTI
> gets those four observables there. Measurement only — nothing here is built or shipped.

## 0. Process note, up front

**No `SendMessage` tool was present in my actual toolset** (Read/Write/Edit/Bash/Grep/Glob
only), despite the brief instructing me to message `backend-dev` directly. I could not
literally send it anything. **Substitute channel used:** I read `backend-dev`'s own journal
(`.claude/journals/backend-dev.md`), which shows it is running, right now, **the identical
task** — same deliverable path (`docs/evidence/cleanplate-mti-measured.md`), same script
under test, its own independently pre-registered bar. That is a **dispatch collision**, not
a division of labour: two agents were hired for the same artifact. I did not overwrite its
work; I did not wait for it either (no channel to actually coordinate timing). This file is
my own narrower measurement, scoped to the founder's four solver observables specifically,
not backend-dev's broader lock-rate/corner-error bar. **The lead needs to reconcile the two
files/verdicts** — see the collision note again at the bottom.

## 1. Has `eval_court_cleanplate.py` ever actually been run?

**Yes, once, on 2026-07-15 — real, not a bare self-claim (T24 checked), but stale and
never re-tracked.** `git log --all -- tools/eval_court_cleanplate.py` shows exactly one
commit ever (`dd2369f`), which both created the file and reports numbers in its own
message: *"CLEAN PLATE (eval_court_cleanplate.py): median frames to delete the players
... Done right: median err 14.4 -> 9.1px on the 9 clips with local video ... Measured on
the 20 gold clips: usable(<35px) 11 -> 13/20, median err 24.1 -> 11.5px, and 15/16 = ~94%
lock on visible-line courts."* The file has not been touched since — no second commit,
no output artifact anywhere under `data/output/`, and no row in `docs/STATE.md` (`grep -n
-i "clean.plate" docs/STATE.md` → nothing). So the number was real but has never been
re-verified against the current pipeline, which has changed substantially since (surface
routing shipped `f41a489`, 2026-08-21). `clean_plate_and_motion` in
`tools/court_setup_server.py:39` (added later, `58401dd`, 2026-07-26) cites
`eval_court_cleanplate.py` for the same "scattered frames fade the lines" claim — same
one real 2026-07-15 run, not a second, independent confirmation.

**Why the old number cannot be trusted as current:** the CURRENT no-clean-plate baseline
(shipped router, `f41a489`) already gets median 8.1 px / 12 of 20 on the precision-gate
gold pool — *better* than clean plate's own quoted 11.5 px from July. That is not evidence
clean plate is bad; it is evidence the two numbers are from different pipeline versions
and cannot be compared. A fresh apples-to-apples run against the CURRENT single-frame
path was required — see §2.

## 2. Fresh re-run on current code, 2026-09-06

`backend/.venv/Scripts/python.exe tools/eval_court_cleanplate.py --all`, wall time 54.3s
for all 20 clips (see §5 for the decode-cost breakdown).

**Note on the gold pool:** this script reads `data/gold/*.court.labels.json` — 20 clips,
all named `am_*`. This is a **different pool** from the precision-gate's 20-clip gold
(the `am_hard_utr`-style set with no `.court.labels.json` suffix). Do not read the
numbers below as commensurate with the 8.1 px / 12-of-20 headline elsewhere; they are
this eval's own self-contained scorecard, on its own clips.

```
locked 13/20 clips | usable (<35px) 11/20 | median err 8.6px
```

Per-clip (locked): am_rally32short 1.9, am_usta60 2.7, am_ntrp30 6.2, am_usta40 6.6,
am_rec30 6.9, am_ntrp40 8.3, am_usta45 8.6, am_ntrp45_courtlevel 13.4, am_college 13.6,
am_beginner 33.6, am_lk35 33.5, am_usta45final 71.7, am_ntrp45w 139.9.
No-lock (7): am_classB, am_fr_sud, am_grass1, am_indoor_hard1, am_indoor_hard2,
am_ntrp50, am_wingfield_clay.

**Real-recipe caveat — read before trusting any of the above as a clean-plate result.**
Only **10 of these 20 clips have a local video file** on disk (`data/incoming/...`); the
other 10 point to YouTube URLs with no local copy. `plate_from_video` requires a local
file — when it's absent the script silently falls back to medianing just the handful of
already-extracted **labelled JPG stills**, which is NOT the n=150/span=90s short-window
recipe the mechanism claim rests on (it is closer to the "scattered frames" failure mode
the docstring warns against, just with very few frames). The 10 clips actually running
the real recipe: `am_beginner, am_classB, am_college, am_lk35, am_ntrp30, am_ntrp40,
am_ntrp45_courtlevel, am_rally32short, am_rec30, am_usta45`. Any claim about what
temporal integration buys must be scoped to these 10 — §3 below is scoped that way.

## 3. Per-observable sharpening: near-baseline row/width, single frame vs clean plate

Scoped to the **10 clips with local video** (§2 caveat). For each: single-frame fit =
`court_setup_server.auto_fit` on the first labelled JPG; plate fit = same `auto_fit` on
`eval_court_cleanplate.plate_from_video(vid, n=150, span_s=90.0, start_frac=0.30)`.
Ground truth = mean of the human-clicked `near_bl_doubles`/`near_br_doubles` across every
usable labelled frame in that clip. Error = `|detected − human|` in px, separately for the
ROW ((bl.y+br.y)/2) and the WIDTH (|bl.x−br.x|).

| clip | single row err | plate row err | single width err | plate width err |
|---|---|---|---|---|
| am_beginner | 5.7 | **17.2** | 70.5 | **29.7** |
| am_classB | 3.7 | no lock | 5.0 | no lock |
| am_college | 5.5 | 4.9 | 19.0 | 17.2 |
| am_lk35 | 8.2 | no lock | 7.5 | no lock |
| am_ntrp30 | 1.8 | 1.9 | 6.9 | 5.9 |
| am_ntrp40 | 2.7 | **3.0** | 8.2 | **14.3** |
| am_ntrp45_courtlevel | 2.4 | **3.0** | 26.8 | 4.7 |
| am_rally32short | 1.8 | 0.2 | 4.1 | 0.9 |
| am_rec30 | 29.9 | 3.2 | 6.2 | **14.4** |
| am_usta45 | no lock | 1.7 | no lock | 14.8 |

**Row:** plate beats single on 3 of 7 double-locked clips (college, rally32short,
rec30 — one of them, rec30, by a large margin, 29.9→3.2px, a real occlusion-removal win);
worse on 4 of 7 (beginner notably worse, +11.5px; the other three within ~0.6px, noise-level).
**Not a majority win.**

**Width:** plate beats single on 5 of 7 double-locked clips, including two large wins
(beginner 70.5→29.7, ntrp45_courtlevel 26.8→4.7). **A majority win**, consistent with the
mechanism claim (an unoccluded baseline gives a truer edge-to-edge width) — but two clips
(ntrp40, rec30) get *worse* on width while getting *better* on row, so the plate does not
move the two observables together.

**Lock rate:** plate locks 8/10, single locks 9/10 — plate loses lock on 2 clips single
had (classB, lk35) and gains 1 single didn't (usta45). **Plate does not clearly beat
single-frame lock rate** on this slice; net change is −1.

**Against the founder's ≤2 px bar (both row AND width, the same clip):** only
**`am_rally32short`** clears it with the plate (0.2 / 0.9 px). No other clip gets both
observables under 2 px simultaneously, plate or single. **1 of 8 double-locked clips**, not
a majority, not close to "clean plate sharpens both inputs to the precision the solve
needs." Where the plate helps most (rec30's row, beginner's width) it is still nowhere near
2 px; where it doesn't help, it can make width or lock actively worse.

## 4. Net line: no ground truth exists in this gold set, so it cannot be measured

Checked every clip's `keypoints` dict: `near_bl_doubles, near_br_doubles, near_bl_singles,
near_br_singles, near_sl_left, near_sl_right, near_t` and the `far_*` mirrors — **no net
keypoint of any kind** (no `net_post_left`/`net_post_right`, nothing at `NET_Y`). The only
net-related code in the backend (`calibration.net_tape_clearance`,
`calibration._net_height_at_x`) *verifies* a net against an **already-known** homography —
neither is a net-line pixel detector, and there is no independent one in this repo. The
prior net-anchor QA work (`docs/evidence/net-anchor-qa-verification.md`) built an ad hoc
brightness-profile detector for a *different* purpose (checking whether a homography's
predicted net row agreed with the visible tape) and did not produce click-level ground
truth either.

**Consequence for the founder's geometry:** the solve is *most* sensitive to the width
RATIO `k = w_near/w_net`, not the rows — and I can measure `w_near` error here (§3) but have
**no way to measure `w_net` error at all** without either (a) new human net-line clicks
(out of scope — I do not create ground truth) or (b) an unbuilt net detector whose own
precision would need validating before it could validate anything else. **This is not a
result of "clean plate doesn't help the net line" — it is that the net-line half of the
founder's four observables is currently unmeasurable, plate or no plate.** That is itself a
finding: the founder's falsifier ("what is the detection precision of the near baseline
*and the net line*") is only half-answerable today.

## 5. Decode cost

Full run (`eval_court_cleanplate.py --all`, all 20 clips, includes both the 10
local-video clips building a real plate and 10 fallback clips that never touch a video
file): **54.3 s wall time total.**

Isolated per-clip decode time for `plate_from_video`, n=150/span_s=90 (the eval script's
own recipe), on the 10 local clips: **0.16 – 1.87 s, mean 1.36 s.** This is far cheaper
than "decoding a minute of video" suggests — `cv2.VideoCapture.set(CAP_PROP_POS_FRAMES)`
seeks to each of the 150 sampled frames rather than decoding the whole 90 s span
sequentially, so cost tracks the number of *sampled* frames, not the span length.

**Pre-registered "as well" bar (declared before running the sweep):** a reduced (n, span)
is *as well as* n=150/span=90 only if it (a) locks the identical clip set AND (b) lands
within 1.0 px of the full setting's row AND width error on every clip both settings lock.

**Swept n=80/span_s=60.0 — the value actually SHIPPED in `court_setup_server
.clean_plate_and_motion`** (not n=150/span=90, which is only in the eval script):

| clip | row err (n=80) | width err (n=80) | decode s (n=80) |
|---|---|---|---|
| am_beginner | 4.7 | 57.4 | 1.00 |
| am_classB | 2.3 (NEW lock) | 9.5 | 1.03 |
| am_college | 6.1 | 27.8 | 0.82 |
| am_lk35 | no lock | no lock | 0.15 |
| am_ntrp30 | 0.9 | 15.2 | 0.71 |
| am_ntrp40 | 3.2 | 15.5 | 0.75 |
| am_ntrp45_courtlevel | 3.6 | 37.2 | 0.95 |
| am_rally32short | 0.4 | 7.6 | 0.70 |
| am_rec30 | 4.0 | 5.6 | 0.79 |
| am_usta45 | 2.4 | 22.1 | 0.70 |

**Result: FAILS the pre-registered "as well" bar, decisively.** The lock set differs
(am_classB now locks, unlike at n=150) and **width error exceeds the 1.0 px tolerance on 7
of 8 double-locked clips**, several by 10–30 px (am_ntrp45_courtlevel 4.7→37.2 px,
am_beginner 29.7→57.4 px). Row error is closer (within 1.0 px on 5 of 8, one exactly at the
1.0 px line, two moderately over) but width — the observable the geometry is *most*
sensitive to (§ founder's note, "the width ratio alone fixes the standoff") — degrades
badly. Mean decode saving vs n=150 is only ~0.6 s/clip (1.36 s → 0.76 s), trivial against
the precision lost.

**Reading these together: the value actually shipped in `clean_plate_and_motion` (n=80,
span=60) is measurably worse than the value this evidence file's own §1/§3 tested (n=150,
span=90) — a real, reportable gap between what was tested and what ships**, on top of the
fact that even the *better* n=150 setting only clears the founder's ≤2 px bar on 1 of 8
clips.

## 6. Verdict

**RETIRES the "clean plate sharpens the inputs enough" hope, on the evidence available.**

- Near-baseline row: **not** a majority win for the plate (3 of 7 double-locked clips
  better, 4 worse) — does not establish sharpening.
- Near-baseline width: a majority win (5 of 7) but with two regressions and no case coming
  close to 2 px except one clip (rally32short) that was already close single-frame.
- **Only 1 of 8 double-locked clips (am_rally32short) meets the founder's ≤2 px bar on
  BOTH observables with the plate** — nowhere near "temporal integration gets this idea
  over the line."
- **The net-line half of the observables cannot be measured at all** in this gold set — no
  ground truth exists — so the founder's own falsifier is only half-testable today. This is
  a gap, not a negative result, for that half.
- **The shipped default (n=80/span=60) is worse than the tested recipe (n=150/span=90)** on
  the very observable (width) the geometry needs most — a live discrepancy between what was
  measured and what runs, independent of the founder's question.
- Lock rate does not clearly favor the plate either (8/10 vs 9/10 single-frame, on this
  slice).

**This does not resolve the founder's question — it narrows it sharply.** The near-baseline
row/width measurement here is real and reproducible; the net-line half needs a detector
that does not exist yet before anyone can answer whether temporal integration helps it too.
Composing this with `backend-dev`'s raw (no-plate) near-line precision number is the
obvious next step but could not be done this run — see the collision note below.

## 6b. CORRECTION — my §3 numbers are NOT on backend-dev's protocol, found too late to redo

`docs/evidence/near-line-detection-precision.md` did not exist when I began measuring; it
appeared mid-run (its §1 "shared protocol" is dated 2026-09-06, timestamped after my §2/§3
runs). Reading it now, **my §3 measurement diverges from its pre-registered shared protocol
in three ways that matter**:

1. **Units.** Its protocol fixes everything in **px@640** (resized to width 640) because the
   8.1/6.4/2.0 px bars are all px@640 — a native-resolution number is 2–3× off and not
   comparable. My §3 numbers are at **native gold-frame resolution**, un-resized. They are
   *not* directly poolable with backend-dev's numbers or the founder's bars without a
   rescale I did not apply.
2. **Truth source.** Its protocol uses `data/<clip>_pts.json` (a 4-corner set); I used
   `data/gold/*.court.labels.json` (a different, larger-keypoint-set gold pool, §2's
   caveat). Different clips, not the same population.
3. **Detection method.** Its protocol measures the **raw shipped line detector**
   (`line_ridge_mask` → `_detect_lines`) matched truth-seeded against a projected line — pure
   localisation precision. I measured the **output of the full `auto_fit` pipeline**
   (structure-matching, voting, roll-lock, verify_court refusal) reading off the corner
   points — a mix of localisation *and* every downstream fitting decision. My numbers answer
   "does the plate change what the shipped court-fit tool outputs," which is a real and
   useful question, but it is **not** the same question as "does the plate sharpen raw line
   detection" that backend-dev's protocol isolates.

**Also corrected: net-line ground truth is NOT actually unmeasurable**, contrary to my §4
above. Backend-dev's protocol shows the right move — project the net's known court-metre
position (`y = 11.885 m`, court.py's `net_post_left`/`net_post_right` or the net **ground**
row) through the SAME homography fitted from the 4 human-clicked corners, exactly as
`eval_court_cleanplate.py` already does for rendering (`calibration.court_to_image(H,
[court.LANDMARKS[...]])`). No net click is required because net position in court metres is
fixed regulation geometry. **I was wrong to call it unmeasurable in §4** — I simply didn't
have backend-dev's protocol yet when I wrote it. I did not redo §3/§4 with this fix or on
backend-dev's protocol given budget; that is squarely **NOT ESTABLISHED THIS RUN** (below).

**Net effect: treat §3's row/width numbers as a real, reproducible measurement of "does
clean-plate change the shipped fitting tool's near-baseline output" — informative on its
own — but do NOT read them as commensurable with backend-dev's px@640 raw-detector numbers
or with the founder's ≤2 px bar without rescaling and re-deriving on the shared protocol.**
The qualitative verdict in §6 (near-baseline sharpening is weak/mixed, nowhere close to a
consistent ≤2 px win) is likely to survive a redo — the effect sizes are mostly far larger
than a 2–3× unit-scale factor could explain (e.g. rec30's 29.9→3.2 px row win, or
beginner's 70.5→29.7 px width win) — but this is a judgement call, not a proof, and the
borderline cases (ntrp30 row 1.8→1.9, ntrp45_courtlevel row 2.4→3.0) could flip under a
proper rescale.

## 7. Exchange with backend-dev, and the dispatch collision

**No `SendMessage` tool exists in my toolset** — I could not literally send `backend-dev`
anything, contrary to what the brief assumed. Substitute channel: I read `backend-dev`'s
own journal (`.claude/journals/backend-dev.md`), which shows it is running, concurrently,
**the same clean-plate-MTI measurement task**, with the same deliverable path
(`docs/evidence/cleanplate-mti-measured.md`) and its own pre-registered bar (lock ≥60% of
corpus + beats blank-rectangle baseline on a majority + beats single-frame on a majority of
overlap clips; mechanism bar = line-support fraction higher on the plate for a majority of
clips; cost bar = reduced (n,span) within 2.0 px on every double-locked clip). That is a
**broader, corner-error-based bar**, different from mine (the founder's four specific
solver observables), but overlapping enough that **both files are being written to the same
path by two agents at once**. I did not overwrite backend-dev's content and could not
coordinate write order — **the lead needs to reconcile the two write-ups** (mine is scoped
to near-baseline row/width + net-line-gap + n-sweep; backend-dev's is presumably scoped to
overall lock/corner-error vs blank-rectangle/single-frame baselines per its own journal).
I also could not obtain or use `backend-dev`'s raw (no-plate) near-baseline precision
number from `docs/evidence/near-line-detection-precision.md` because that file does not
exist yet as of this run (`ls docs/evidence/near-line-detection-precision.md` → not found).
The composed "extrapolated far-baseline error with temporal integration" the brief asks for
therefore **could not be produced this run** — it needs both numbers to exist at the same
time, which they did not.

**NEEDS DISPATCH:** none filed as a retry request (per the rules, a request is stated once,
not chased) — but the lead should note the **dispatch collision** (two agents, one
deliverable path, `docs/evidence/cleanplate-mti-measured.md`) and decide which write-up (or
merge) stands, and should sequence `backend-dev`'s raw near-line-precision number and this
file's plate-sharpening factor into one composed answer once both exist.

## NOT ESTABLISHED THIS RUN

- **A redo of §3 on backend-dev's shared protocol** (px@640 units, `data/*_pts.json`
  population, raw `line_ridge_mask`/`_detect_lines` matching instead of full `auto_fit`
  output) — needed before my number and backend-dev's are truly comparable. See §6b.
- Net-line detection precision, with or without the plate. **Correction: this is not
  actually unmeasurable** (§6b) — it can be derived by projecting `court.LANDMARKS`'
  net-ground row through the human-fitted homography, same as `eval_court_cleanplate.py`
  already does for rendering. Not done this run; §4's "unmeasurable" claim was written
  before I had backend-dev's protocol and should be read as "not done," not "impossible."
- The composed end-to-end "extrapolated far-baseline error with temporal integration"
  number the brief's item 4 asks for (needs backend-dev's raw near-line number, which does
  not exist yet as a file this run).
- Whether backend-dev's own run (same task, same file) reached the same or a different
  verdict — could not be read/merged, no coordination channel available.
- A mechanism check on WHY am_beginner and am_ntrp40/am_rec30 move in different directions
  under the plate (visual inspection of the plate images themselves, per "render before
  claiming" — not done this run, budget-limited).
