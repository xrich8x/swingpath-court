# The references pool drops 20 → 16, and the list of numbers that go stale

**backend-dev, 2026-09-09.** Implementation of the founder's strict "one camera setup"
ruling, plus the invalidation list it requires.

**NOTHING HERE WAS RE-MEASURED.** No eval was run to produce a figure. Every number
quoted below is quoted **as published**, from the file named beside it, and is marked
stale — not corrected, not re-based. Re-measuring against 16 needs its own
pre-registered bar and was explicitly not authorised. A new denominator is not a
licence to re-run and keep whichever number comes out better.

---

## 1. The ruling, and where it now lives in code

A clip belongs in `eval/run_refs.references()` only if one camera setup covers its
**scored** frames (`run_refs.frame_positions(total, 8)`, 5%–95% of the clip) **and** the
background stays within the project's own `WRONG_PX_640 = 20.0` across them. That is
qa's `S20` quantity from `docs/evidence/clip-shot-map.md` — **no new constant was
introduced**; the strict rule re-uses the shipped wrong-court line and nothing else.

Why the looser bar was not enough, in qa's own words: an ORB/RANSAC *similarity* edge
proves only that two frames share a **registrable** background, which a hard
pan-and-zoom still satisfies. Measured *inside* the winning group, `A7vXlWIlyrI` moves
**188.3 px@640 with a 40% zoom while scoring 8/8** — nine wrong-court distances. One
homography cannot describe that. The lead confirmed it by eye (eval samples 1 and 8 are
visibly different zooms with the corner marks in near-identical pixel positions).

Second, independent reason (`docs/evidence/court-triage-2026-09-09.md`): all four are
**edited YouTube with cuts and zooms**, while the product's own footage is one
continuous take. They are unrepresentative of anything this app will ever see.

**Implemented in `eval/run_refs.py` as `EXCLUDED_CLIPS`** — a clip → reason map sitting
immediately above `references()`, each entry quoting the measured `S20`, the max
intra-group displacement and the max zoom, and `exclusion_note()` printing it to stderr
on every call, ahead of the existing provenance warning.

**It was deliberately NOT implemented by moving files.** `references()` globs
`data/*_pts*.json` **non-recursively**; `bump_ntrp30` and `bump_ntrp30b` sat in
`data/amateur_clips/` for weeks, invisible to that glob, absent from every measurement,
with nobody aware. The four dropped `*_pts.json` files stay exactly where they are,
still `_exact`, still globbed — and `backend/tests/test_refs_pool_strict16.py` asserts
that they do, so a future "cleanup" that hides them fails loudly.

`uR5q2cSM6AY` is the **marginal fifth** (`S20 = 5`, one frame short of
`ACCEPT_VOTES = 6`, at 20.5 px@640 and 0.6% zoom — it misses by half a pixel, not by a
re-frame). The ruling **RETAINS and flags** it, and forbids widening the rule to catch
it. It is named in `FLAGGED_MARGINAL` and the test fails if it ever leaves quietly.

### The four, with the measurement each failed

| Dropped clip | `S20` | max displacement in-group | max zoom | note |
|---|---|---|---|---|
| `A7vXlWIlyrI` | 3 / 8 | **188.3 px@640** | **40.0%** | worst zoom; confirmed by eye |
| `HoHxFSX_gLk_s1` | **1 / 8** | 189.5 px@640 | 42.2% | worst in the population; also failed the ORIGINAL bar at `G = 5` |
| `HoHxFSX_gLk_s2` | 3 / 8 | 105.9 px@640 | 28.5% | passed the original bar at exactly `G = 6`, on the line |
| `UHf0LeMU2pg` | 4 / 8 | 28.2 px@640 | 1.1% | a clean **cut** at frame 4198, not a zoom |

All four measurements are qa's, from `docs/evidence/clip-shot-map.md` §5.

---

## 2. Before and after

**BEFORE — 20 clips** (`references()` prior to this change):

```
A7vXlWIlyrI      am_hard_utr       CYqapSq5llo       e8T34KoJzOw_s2
flexi_franz_p01  flexi_franz_p07   flexi_joy_p01     flexi_joy_p07
hillsborough_p02 hillsborough_p08  HoHxFSX_gLk_s1    HoHxFSX_gLk_s2
mpc_mixed_p02    mpc_mixed_p08     mpc_tuesday_p01   mpc_tuesday_p07
sAjkpeRq4P4      tc8CGFxyRE8       UHf0LeMU2pg       uR5q2cSM6AY
```

**AFTER — 16 clips** (verified by running `references()`; the four names above are
absent, `uR5q2cSM6AY` is present):

```
am_hard_utr      CYqapSq5llo       e8T34KoJzOw_s2    flexi_franz_p01
flexi_franz_p07  flexi_joy_p01     flexi_joy_p07     hillsborough_p02
hillsborough_p08 mpc_mixed_p02     mpc_mixed_p08     mpc_tuesday_p01
mpc_tuesday_p07  sAjkpeRq4P4       tc8CGFxyRE8       uR5q2cSM6AY
```

`HoHxFSX_gLk_s1` and `_s2` share a source video, so this costs **one recording, not
two**.

### The composition change is larger than the count change

All four dropped clips are **1920-wide hardcourt**. The shell block is untouched.

| | before | after |
|---|---|---|
| Shell (3840) | 10 | **10** |
| Hardcourt (1920) | 8 | **4** |
| Clay (1920) | 2 | **2** |
| **non-shell total** | **10** | **6** |
| shell share of the pool | 50% | **62.5%** |

**This is the part that matters for re-basing.** The pool lost 20% of its clips but
**40% of its non-shell half**, and shell is the surface every court number is worst on.
Any figure split by surface is affected far more than its headline suggests. Scored
frames go 160 → 128.

### A hazard worth stating plainly

Joining against the founder's 2026-09-09 corner review as re-stated in `docs/STATE.md`
(row 243: in-pool tally **2 MISPLACED, 4 MIXED, 1 exonerated, 13 untouched**), the four
dropped clips are **both MISPLACED clips and 2 of the 4 MIXED**. After the drop the pool
contains **0 confirmed-misplaced clips**.

The pool therefore *looks* cleaner — because the contested clips left, not because
anything was re-placed. Do not read the strict ruling as having resolved T26. The
remaining calibrations carry exactly the provenance they carried yesterday.

---

## 3. THE INVALIDATION LIST

"Moves it?" answers only *does the drop plausibly change this number*. It is not a
restatement and no restated value is given.

### 3a. Directly scored against `references()` — STALE

| File | Row / section | Number as published | Moves it? |
|---|---|---|---|
| `docs/evidence/candidate-proposal-recall.md` | headline §1 | proposal recall **8/20 = 40%** | **YES.** Read off that file's own per-clip table, the drop removes **1 reached** clip (`A7vXlWIlyrI`, 5.3 px) and **3 never-reached** (`HoHxFSX_gLk_s2` 23.1, `UHf0LeMU2pg` 35.7, `HoHxFSX_gLk_s1` 60.5), so the ratio moves **upward**. Re-basing alone does **not** cross the pre-registered 60% "search binds" line, so the VERDICT survives; the FIGURE does not. |
| same | §1, §7 | "on **12 of 20** clips the search never once produces a court within 20 px" | YES — same arithmetic, 3 of the 12 leave |
| same | §5 tolerance sensitivity | **8/20** at 20 px and 22 px, **10/20** at 30 px and 35 px | YES — every cell |
| same | §5 surface split | Hardcourt **4/8 = 50%**, 3/7 recordings, median 38.8 px | **YES, worst hit** — the hardcourt row loses half its clips (8 → 4) |
| same | §4 | "a court a median 4.9 px from the clicks clears the accept gate on **19 of 20**" | **YES, and it changes character** — the single failure was `UHf0LeMU2pg`, which is dropped. The one counterexample leaves the pool. Do not re-base this to a clean sweep without a pre-registered re-measurement. |
| same | §4 | `truth_would_pass = 9/20` | already **RETRACTED, do not quote** (unchanged advice) |
| `docs/evidence/cnn-global-classical-local.md` | summary row, Result 2 | classical arm **References 2/20**, CourtNet **0/20** | **DENOMINATOR ONLY.** Both accepted clips (`am_hard_utr`, `sAjkpeRq4P4`) are **retained**, so the numerator is unchanged; the rate rises purely by removing non-accepts. |
| same | Result 2 | **3 of 160 frames locked vs 89** | YES — frames 160 → 128; arm A loses 22 locks (4+3+8+7), arm B loses 1 (`UHf0LeMU2pg`) |
| same | Result 2 surface table | Hardcourt **n = 8**, 1 accepted | YES — n → 4 |
| same | line 113 | "documented shipped baseline for this population is **2/20** with shell 0/10" | denominator; shell 0/10 untouched |
| `docs/evidence/camera-motion-vs-court-agreement.md` | headline, §1 | **0 of 20** clips change acceptance; accepts **2 of 20**; **4 of 20** unmeasurable; FULL TABLE "20 clips"; injected 8.000 px recovered on **all 20** | **YES, and this file is the most affected of all** |
| same | §1 | "**1 of 16** measurable clips crosses the 20 px line (`HoHxFSX_gLk_s2` 41.6 → 15.7)" | **YES — that clip is dropped.** The single crossing case leaves the pool. |
| same | §1 | "the **5 clips that genuinely move** inside the scored window" vs "the **11 that do not**"; `rho(M_win, D_raw) = 0.474` at **n = 16** | **YES, structurally.** The moving group is largely the dropped set; the correlation's whole contrast range is gutted. Treat the motion analysis as measured on a population that no longer exists. |
| `docs/evidence/court-correspondence-gate.md` | "current" table | reference clips (1920) auto-accepted **2 of 20** | denominator |
| same | **C4, a PRE-REGISTERED gate** | "references **2/20 → ≥4**" | **YES — restate the gate explicitly.** A pre-registered bar whose denominator moved must be re-stated in writing before anything is judged against it. Do not silently reinterpret "≥4" against 16. |
| same | §tau sweep | "TUNE (gold + 1920 refs)" tuning population | population changed; any tau tuned on it was tuned on 20 |
| `docs/evidence/scaling-the-court-refiner-s-reach-with.md` | headline | references **2/20 → 2/20** | denominator only; the *no-op* claim itself is unaffected (it was exact) |
| `docs/evidence/agree-px-is-6-tighter-on-4k.md` | §1 | "on the 1920 references it admits two wrong courts — `tc8CGFxyRE8` 58.7 px, `e8T34KoJzOw_s2` 28.7 px" | **finding SURVIVES** — both clips retained. Only the surrounding "the references are 1920" population description is stale. |
| `docs/evidence/least-squares-court-fit.md` | per-pool table | TUNE (gold + 1920 refs) **n = 8**, 19.00 / 23.50 / 123.37 px | **UNKNOWN — check before requoting.** The row does not state which refs are in its n = 8. If any dropped clip is, the cell moves. |
| `data/output/court_scoring_diagnosis.md` | §10 (line 302) | "clears the accept gate on **19 of 20** ... only `UHf0LeMU2pg` fails" | **YES — the sole counterexample is dropped** (same caution as above) |
| same | line 224 | "12/20 gold at 15.2 px, **3/10 refs** at 14.2 px" | **YES** — "10 refs" is the non-shell subset, which goes 10 → 6 |
| `docs/evidence/calibration-provenance.md` | §1, §5a, warning text | "the **20-clip** court scoring pool"; "**6/20** clips written by 3399d58 or ac94aab"; "**9 of 20** from the wider agent session"; §5a's 20-clip listing | **YES.** All four dropped clips are in `FLAGGED_SESSION`, and three of them in `FLAGGED_COMMITS`. The warning text is computed at runtime and now prints **3/16** and **5/16** — so the published 6/20 and 9/20 no longer match what the tool prints. |
| same | §5 | "`references()` returns byte-identical, **20 clips**, same order" | that rule-8 no-op claim was true **of that change** and stays true; the pool it names is now 16 |
| `docs/TRAPS.md` | **T26** | "**9 of the 20 clips** in the scoring pool come from that batch"; wrong-rate in-batch ~73%, outside ~12% | **YES** — 9/20 → the tool now prints 5/16. (T26's text itself is the lead's to amend; TRAPS IDs are never renumbered.) |
| `docs/STATE.md` | row 196 (CNN-global) | "References: **2/20 → 0/20**", "3 of 160 frames locked against 89" | YES — as above. *(STATE is the lead's; listed, not edited.)* |
| `docs/STATE.md` | row 197 (proposal recall) | **8/20 = 40%**, 12 of 20, 8/20 at 20–22, 10/20 at 30–35, 19 of 20 | YES — as above |
| `docs/STATE.md` | row 241 (camera motion) | 0 of 20 acceptance, 1 of 16, n = 16, 2/20, all 20 | YES — as above |
| `docs/STATE.md` | row 243 (T26 provenance) | "returns the identical **20** clips"; in-pool tally **2 MISPLACED / 4 MIXED / 1 exonerated / 13 untouched**; "proposal recall can rise to at most **10/20 = 50%**" | **YES, and see §2's hazard** — the ceiling argument is built on the 20-clip pool and the tally's contested clips have left it |
| `docs/evidence/clip-shot-map.md` | §6, §7 | "the references pool is **20 clips**"; "Pool 20 → 16 (or 15)" | **SUPERSEDED, not stale** — this is the evidence the ruling was taken on. §7's "(or 15)" is now resolved: 16, `uR5q2cSM6AY` retained. |

### 3b. Affected going forward, not retrospectively

These eleven scripts import `run_refs.references()` and will now score 16 clips. Nothing
they have already published changes because of the import — but any **new** run of them
is on a different population, and comparing a new run to an old table is not a
like-for-like A/B:

`eval/behind_camera.py`, `eval/candidate_audit.py`, `eval/crop_safety.py`,
`eval/evid_band_sweep.py`, `eval/movers.py`, `eval/proposer_ab.py`,
`eval/proposer_rejects.py`, `eval/reach_ab.py`, `eval/score_truth.py`,
`eval/tol_sweep.py`, `eval/truth_neighbourhood.py`.

`tools/render_ai_court_audit.py` also defaults its clip list to `references()`; its
docstring and `--clips` help said "the 20-clip gold pool" and were corrected. A dropped
clip can still be rendered by naming it explicitly — the exclusion is a **scoring-pool**
decision, not a ban on looking at the frames.

### 3c. NOT AFFECTED — do not re-base these

Listing them matters as much as listing the stale ones. There are **three** different
20s in this project and only one of them moved.

- **The 12/20 gold gate and everything scored against `data/gold/<clip>.court.labels.json`.**
  A different 20-file truth set: different clip names (`am_beginner`, `am_classB`,
  `am_college`, …), all 640 wide, written by a different tool. Covers
  `docs/STATE.md` rows 88 and 105, `cnn-global-classical-local.md` **Result 1**
  (gold 12/20 → 2/20, 11 of 20, 17 of 20 in training),
  `court-mask-sweep-item-is-already-shipped.md` (12/20, 11/20),
  `court_consensus_bar.md` (11 of 20), `court_breadth_54.md` (11/20),
  `cleanplate-mti-measured.md` (13/20, 11/20 — a `data/gold` pool again),
  `mobile-viability-audit.md` (12/20), `the-horizon-crop-…` and
  `far-player-motion-contrast-hypothesis.md` (1 of 20 gold).
- **Every shell figure.** All 10 shell references come from commit `7c8b8af` and none is
  dropped: shell **0/10** accepted, shell **1 of 5 recordings** reached, **20/80 → 0/80**
  frames, the shell arm of every surface split.
- **The BALL gold clips `gold_UHf0LeMU2pg` and `gold_uR5q2cSM6AY`.** Same underlying
  match, entirely different pool and task (`bounce-hypothesis*.md`,
  `ballnet-v21-vs-tracknet-at-the-chain.md`). A court-pool ruling does not touch ball
  gold, and the shared basename is exactly the sort of coincidence that gets one
  mistaken for the other.
- **Populations built by enumerating calibrations directly rather than via
  `references()`** — the 28-calibration sweeps: net tape **13/15**, net post **3/11**,
  `live-setup-criterion.md`'s 28 clips / 16 poor / 6 marginal / 6 good,
  `composite-calibration-score.md`, `camera-motion-verdict-risk.md`'s 28 rendered
  sheets. **The ruling excludes clips from a scoring pool; it deletes no calibration
  file.** These populations are unchanged. (`camera-motion-verdict-risk.md` still
  *describes* four clips that are now outside the pool — true statements about clips
  that no longer set any court number.)

---

## 4. What changed in code

| File | Change |
|---|---|
| `eval/run_refs.py` | `WRONG_PX_640 = 20.0` (copied from the shipped constant, not new), `EXCLUDED_CLIPS` with a per-clip reason, `FLAGGED_MARGINAL`, `exclusion_note()` printed to stderr before the provenance warning, module and `references()` docstrings restated to 16 with the stale-figure warning |
| `backend/tests/test_refs_pool_strict16.py` | **new, 13 tests** — pool is 16; the four are absent; `uR5q2cSM6AY` present; the exclusion names exactly four clips, each with a reason quoting `S20`; `WRONG_PX_640` still equals `candidate_audit.WRONG_PX_640`; the four `*_pts.json` are still on disk, still `_exact`, still globbed; and the 20 − 4 = 16 arithmetic reconstructed from disk |
| `tools/render_ai_court_audit.py` | docstring + `--clips` help no longer claim a "20-clip gold pool" |

No `*_pts.json` was read for content, edited or moved. `data/pre_reaudit_backup/` was
not touched. `docs/STATE.md` is the lead's and was not edited — the ruling is already
recorded there at row 239.
