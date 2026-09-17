# Clip shot map: can these clips support a single calibration at all?

**qa, 2026-09-09.** Independent verification run. Measurement of **clip structure only**.
I did not judge, edit or re-place any corner placement, and nothing in this file says
anything about *why* any placement is wrong — a clip can be single-setup and still badly
calibrated. Raw data: `scratchpad/shot_map.json` (session `aad66fbf`), script
`scratchpad/shot_map.py`.

This run was killed twice by usage limits. The bar below was pre-registered in
`.claude/journals/qa.md` **before any pair was estimated**, survived both kills, and is
reproduced here verbatim. It was not re-derived after seeing results.

---

## 1. Control result, stated first

| Control | Required | Measured | Result |
| --- | --- | --- | --- |
| **`sAjkpeRq4P4` (positive, pre-registered stop condition)** | `G = 8` | **`G = 8`**, 28/28 pairs linked, one component | **PASS** |
| `flexi_joy_p01` (static shell tripod) | `G = 8` | `G = 8`, 28/28, max intra-pair displacement **0.4 px@640** | PASS |
| `hillsborough_p02` (static shell tripod) | `G = 8` | `G = 8`, 28/28, max intra-pair displacement **0.1 px@640** | PASS |
| Null (each clip's frame vs itself) | edge, ~0 px | edge on **12/12**, `0.000 px@640` on all 12 | PASS |
| Positive (+8.000 px@640 injected shift) | edge, ~8 px | edge on **12/12**, recovered **7.91–8.05 px@640** | PASS |
| **Negative (a frame vs a frame from a *different* clip)** | **no edge** | **no edge on 11/11** (3–12 inliers, all below the 30 cut-off) | PASS |

The negative control is the one that actually validates the grouping: the criterion is
capable of saying "different setup", and does so on genuinely unrelated footage. The
grouping is therefore trusted, and the rest of this file stands.

---

## 2. The pre-registered bar (verbatim from the journal)

An edge between two of the 8 sampled frames = "same camera setup", requiring **both**:
- **E1** `>= 30` RANSAC inliers on the ORB background match;
- **E2** sane similarity: `0.5 <= scale <= 2.0` and `|rotation| <= 30 deg`.

`G(c)` = size of the largest **clique** (a set of frames all pairwise linked at once),
enumerated exhaustively over `n = 8`.

Bar, justified from `courtfit.ACCEPT_VOTES = 6` of `ACCEPT_K = 8` — a calibration can
only be accepted if >= 6 of the 8 sampled frames agree with it:
- **PASS (RE-PLACEABLE)**: `G(c) >= 6`
- **FAIL-RESTRICT**: `2 <= G(c) <= 5`
- **FAIL-DROP**: `G(c) <= 1`

**Recorded caveat, restated as required: 6/8 is NECESSARY, NOT SUFFICIENT.** A clip can
clear this bar and still be uncalibratable for reasons this measurement cannot see.
Section 5 shows that this caveat is *load-bearing here*, not boilerplate.

**Disclosed discrepancy in my own bar.** The journal text says E2 "re-uses run 3/4
unchanged"; run 3/4's code actually used `0.33 <= scale <= 3.0` and `|rot| <= 25 deg`.
I honoured the journal's E2 as written and ran the run-3/4 numbers as a sensitivity
check: **`G` is identical on all 12 clips under both.** The discrepancy is a no-op and I
did not swap the bar to make it one.

---

## 3. Per-clip result

Frame indices are `eval/run_refs.frame_positions(total, 8)`. Video frame 0 is **not** one
of them and never entered the grouping (the covariate trap from run 4).

| Clip | Founder verdict | 8 sampled frames grouped into setups | `G` | CC | Verdict vs bar |
| --- | --- | --- | --- | --- | --- |
| `sAjkpeRq4P4` | HOLDS | **{5262, 18795, 32328, 45861, 59393, 72926, 86459, 99992}** — one setup | **8** | 8 | **PASS** (control) |
| `HoHxFSX_gLk_s1` | MISPLACED | {158, 1384, 1792, 2201, 3018} · {567} · {975} · {2609} | **5** | 5 | **FAIL-RESTRICT** |
| `HoHxFSX_gLk_s2` | MISPLACED | {1143, 4083, 7023, 9963, 12903, 15843} · {18783, 21723} | **6** | 6 | **PASS** (borderline — exactly on the line) |
| `HoHxFSX_gLk_s3` | MISPLACED | {160, 572, 984, 2632} · {1396, 1808, 2220} · {3044 = decode fail} | **4** | 4 | **FAIL-RESTRICT** |
| `bump_ntrp30` | MISPLACED | all 8 — one setup by the bar's test | **8** | 8 | **PASS** (see §5) |
| `A7vXlWIlyrI` | MIXED | all 8 — one setup by the bar's test | **8** | 8 | **PASS** (see §5) |
| `CYqapSq5llo` | MIXED | all 8 — one setup | **8** | 8 | **PASS** |
| `UHf0LeMU2pg` | MIXED | all 8 — one setup by the bar's test | **8** | 8 | **PASS** (see §5) |
| `uR5q2cSM6AY` | MIXED | all 8 — one setup | **8** | 8 | **PASS** |
| `bump_ntrp30b` | MIXED | all 8 — one setup by the bar's test | **8** | 8 | **PASS** (see §5) |
| `flexi_joy_p01` | (neg control) | all 8 | **8** | 8 | PASS |
| `hillsborough_p02` | (neg control) | all 8 | **8** | 8 | PASS |

**Tally against the bar: 8 PASS (incl. the control and 2 negative controls), 2
FAIL-RESTRICT, 0 FAIL-DROP.** No clip in this population fails to support *any* window.

`HoHxFSX_gLk_s3` frame `3044` failed to decode (the same failure recorded in
`docs/evidence/camera-motion-verdict-risk.md`). It is counted as **isolated**, never as
part of a group — so it can only lower `G`, never inflate it. Its clip is FAIL-RESTRICT
on 21 measured pairs out of 28.

---

## 4. How I handled non-transitivity, rather than assuming it away

"Same setup" is a noisy relation and need not be transitive: a chain of weak links can
merge two genuinely different setups. So I computed **both** groupings and report both:

- **CLIQUE (strict, primary)** — the largest set of frames that are *all pairwise*
  linked. This is primary because a calibration placed on one frame must hold on every
  other frame in the group *simultaneously*, which is exactly the pairwise-simultaneous
  condition the 6-of-8 vote imposes. `n = 8`, so all 256 subsets were enumerated —
  exact, not heuristic.
- **CC (optimistic bound)** — connected components under transitive closure.

**Result: `CC_max == G` on all 12 clips.** The optimistic and the strict grouping agree
everywhere in this population, so no verdict here depends on the choice. Non-transitivity
was measured and did not bite. The two split clips split *cleanly*: `HoHxFSX_gLk_s1` into
5 + three singletons, `HoHxFSX_gLk_s2` into 6 + 2, `HoHxFSX_gLk_s3` into 4 + 3 + 1.

Where a largest clique was tied in size with another, the enumeration returns the first
in index order; ties did not occur at a size that would change any verdict.

---

## 5. The caveat is load-bearing: an edge means "registrable", not "one homography"

This is the most important thing in the file and it is a limitation of **my own
pre-registered instrument**, reported rather than papered over.

E1/E2 ask only whether a common background exists under a *similarity*. A camera that
pans, tilts or re-frames by a large amount still satisfies that — the scene is the same,
so the frames link. **A similarity linking two frames does not mean one homography fits
both.** So `G >= 6` establishes "same venue, registrable background", which is
*necessary* for a single calibration and not *sufficient*.

The size of that gap, measured (max background displacement between frames **inside the
winning clique**, px@640; `WRONG_PX_640 = 20.0` is this project's own wrong-court line):

| Clip | `G` | max intra-clique displacement | median | max zoom within clique |
| --- | --- | --- | --- | --- |
| `hillsborough_p02` | 8 | **0.1** | 0.0 | 0.0% |
| `flexi_joy_p01` | 8 | **0.4** | 0.1 | 0.1% |
| `sAjkpeRq4P4` | 8 | **6.3** | 2.7 | 0.2% |
| `uR5q2cSM6AY` | 8 | **20.5** | 19.2 | 0.6% |
| `UHf0LeMU2pg` | 8 | **28.2** | 25.9 | 1.1% |
| `CYqapSq5llo` | 8 | **38.1** | 3.8 | 2.9% |
| `bump_ntrp30b` | 8 | **40.2** | 40.0 | 0.1% |
| `bump_ntrp30` | 8 | **60.5** | 60.3 | 0.1% |
| `HoHxFSX_gLk_s2` | 6 | **105.9** | 33.8 | 28.5% |
| `HoHxFSX_gLk_s3` | 4 | **138.5** | 81.6 | 37.3% |
| `A7vXlWIlyrI` | 8 | **188.3** | 130.3 | 40.0% |
| `HoHxFSX_gLk_s1` | 5 | **189.5** | 78.1 | 42.2% |

`A7vXlWIlyrI` clears the bar at `G = 8` while its background moves **188 px@640** and
zooms **40%** across the window. That is nine wrong-court distances. It is one continuous
venue with a moving broadcast camera, and one homography cannot describe it. The bar, as
pre-registered, calls it PASS. I report it as PASS **and** flag it, because the honest
reading is that my bar screens out clips that were *edited across venues*, not clips
whose *camera moved*.

I did **not** move the bar to absorb this. Instead I report a clearly-labelled secondary
quantity that uses no new threshold of mine: `S20(c)` = the largest set of frames that
are all pairwise linked **and** all pairwise within `WRONG_PX_640 = 20.0` px@640 — the
project's existing constant, not one I invented after seeing results.

| Clip | `G` (the bar) | `S20` (secondary, not the bar) | the `S20` frames |
| --- | --- | --- | --- |
| `sAjkpeRq4P4` | 8 | **8** | all |
| `flexi_joy_p01` / `hillsborough_p02` | 8 | **8** | all |
| `CYqapSq5llo` | 8 | **7** | 18129, 31181, 44234, 57286, 70339, 83391, 96444 |
| `uR5q2cSM6AY` | 8 | **5** | 3814, 9307, 14799, 17546, 20292 |
| `UHf0LeMU2pg` | 8 | **4** | 372, 1329, 2285, 3242 |
| `bump_ntrp30` | 8 | **4** | 45, 161, 276, 392 |
| `bump_ntrp30b` | 8 | **4** | 45, 161, 276, 392 |
| `HoHxFSX_gLk_s2` | 6 | **3** | 9963, 12903, 15843 |
| `A7vXlWIlyrI` | 8 | **3** | 26943, 38221, 49499 |
| `HoHxFSX_gLk_s3` | 4 | **2** | 984, 2632 |
| `HoHxFSX_gLk_s1` | 5 | **1** | 158 |

`S20` independently reproduces the step positions found in run 3 from a completely
different direction: `bump_ntrp30` / `bump_ntrp30b` split at frame **508** (the `S20` set
is exactly the four pre-508 frames), `UHf0LeMU2pg` at **4198**, `CYqapSq5llo` drops only
frame **5076**. Two instruments agreeing on the same cut positions is why I trust the
grouping.

**`S20` is NOT the bar and I am not substituting it for one.** It is handed to the
founder as the tight reading; the bar's verdict stands as written.

---

## 6. Per-clip recommendation

Primary column is the bar. Where the two readings differ I say so rather than picking.

| Clip | In the 20-clip pool? | Recommendation **by the bar** | Under the tight (`S20`) reading |
| --- | --- | --- | --- |
| `sAjkpeRq4P4` | yes | **RE-PLACEABLE** — any/all 8 frames; control, verdict HOLDS anyway | RE-PLACEABLE, all 8 |
| `CYqapSq5llo` | yes | **RE-PLACEABLE** — stage on any of 18129 / 31181 / 44234 | RE-PLACEABLE (7 frames), avoid 5076 |
| `uR5q2cSM6AY` | yes | **RE-PLACEABLE** — stage on 9307 or 14799 | RESTRICT (5 frames, one short of the vote) |
| `UHf0LeMU2pg` | yes | **RE-PLACEABLE** — stage on 1329 or 2285 | RESTRICT (4 frames, pre-4198 only) |
| `A7vXlWIlyrI` | yes | **RE-PLACEABLE** by the bar — stage on 38221 | **RESTRICT** — 188 px / 40% zoom; one homography cannot hold |
| `HoHxFSX_gLk_s2` | yes | **RE-PLACEABLE**, borderline (`G = 6`, exactly on the line) — stage on 7023 or 9963; frames 18783/21723 are a second setup | RESTRICT (3 frames) |
| `HoHxFSX_gLk_s1` | yes | **RESTRICT** (`G = 5`) — usable window {158, 1384, 1792, 2201, 3018}, one frame short of the vote | worst in the pool: `S20 = 1` |
| `HoHxFSX_gLk_s3` | **no** | **RESTRICT** (`G = 4`) — window {160, 572, 984, 2632}; second setup {1396, 1808, 2220}; 3044 undecodable | RESTRICT (2 frames) |
| `bump_ntrp30` | **no** | **RE-PLACEABLE** by the bar — but a clean 60.5 px step at 508; stage pre-508 | RESTRICT (4 frames, pre-508) |
| `bump_ntrp30b` | **no** | **RE-PLACEABLE** by the bar — 40.2 px step at 508; stage pre-508 | RESTRICT (4 frames, pre-508) |

**Nothing here is a DROP.** `FAIL-DROP` required `G <= 1` and no clip reached it. If the
founder wants clips dropped, that is a decision taken on the tight reading or on
placement quality, not something this measurement delivers.

---

## 7. Pool-size consequence — the number for the founder to restate in writing

The references pool is **20 clips** (`eval/run_refs.references()`, enumerated this run).
**7 of the 10 population clips are in it**; `HoHxFSX_gLk_s3`, `bump_ntrp30` and
`bump_ntrp30b` are **not** — they are in the population for the founder's decision only.
(`bump_ntrp30`/`b` live under `data/amateur_clips/`, untracked and invisible to
`run_refs.py:132`'s non-recursive glob.)

Of the 7 in-pool clips: 6 are affected (`HoHxFSX_gLk_s1`, `HoHxFSX_gLk_s2`,
`A7vXlWIlyrI`, `CYqapSq5llo`, `UHf0LeMU2pg`, `uR5q2cSM6AY`) plus the control
`sAjkpeRq4P4`, which HOLDS.

- **By the bar as pre-registered: N = 1.** Only `HoHxFSX_gLk_s1` (`G = 5`) fails.
  **Pool 20 → 19. 5% of the references pool leaves.**
- **Under the tight `S20` reading: N = 4.** `HoHxFSX_gLk_s1`, `HoHxFSX_gLk_s2`,
  `A7vXlWIlyrI` and `UHf0LeMU2pg` fall below 6 frames; `uR5q2cSM6AY` at 5 is a fifth,
  marginal case. **Pool 20 → 16 (or 15). 20–25% of the references pool leaves.**

That spread — 5% versus 20–25% — is the decision the founder has to make, and it is a
decision about *which reading of "one setup"* the pool is built on, not about any
number's correctness. **Both numbers come from the same measurement.**

Population-identity note: pool identity keys on the **source video**, not the clip name
(`eval/recordings.py`). `HoHxFSX_gLk_s1` and `_s2` share a source, so removing both
removes one recording, not two.

---

## 8. What this file does NOT establish

- **Nothing about placement quality.** Barred, and honoured. `bump_ntrp30` is
  single-setup by the bar and the founder still marked it MISPLACED; both can be true.
- **`G >= 6` does not mean a calibration will pass the vote.** Necessary, not sufficient
  — and §5 shows the gap is large on at least 4 clips.
- **Nothing about *why* any clip is hard.** Surface, mount height and proposal recall are
  measured elsewhere (`docs/evidence/court-proposal-recall-search-binds.md`).
- **The 10 calibrations under review are still under review.** No number in this file is
  scored against them; this file measures video, not courts. `data/pre_reaudit_backup/`
  is untouched.
