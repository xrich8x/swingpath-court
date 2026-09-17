# Calibration provenance: where the court corners actually came from

**Date:** 2026-09-09 · **Author:** backend-dev · **Scope:** `tools/court_setup_server.py`
`/api/save`, `eval/run_refs.py`, and a git-archaeology record of every
`data/**/*_pts*.json` in the repo.

**Nothing in this document changes a corner value, and no existing file was
backfilled.** Repo rule 9: mislabels get recorded, not fixed. The founder's
2026-09-09 review of the rendered corner sheets is open; re-placing any of these
is his call, not this task's.

---

## 1. The defect

`eval/run_refs.py::references()` gates the whole 20-clip court scoring pool on
`"_exact": true`, and its module docstring asserted that the flag meant:

> *"the overlay tool's shape-lock-OFF save: the user DELIBERATELY placed these
> corners" — so it is a human placement, not a detector output.*

That was false. `tools/court_setup_server.py`'s `/api/save` writes `_exact`
whenever the browser's **Shape lock** checkbox happened to be unchecked when Save
was pressed. It records that the corners were not run through `lock_shape()`. It
records nothing about *who or what* placed them. The tool serves a localhost page
and cannot distinguish a person's mouse from an agent's HTTP POST.

That is the mechanism by which agent-placed corners entered the scoring pool
wearing a human-ground-truth label — and the label was then read back as truth by
`run_refs.py`, `candidate_audit.py`, `proposer_ab.py` and six other eval scripts.

**A second hole in the same handler:** on the shape-lock-**ON** path, Save does
not store the placement it was handed. It runs it through `lock_shape()` and
stores the solver's adjusted corners. The distance moved was returned to the
browser as `moved` and then discarded. So for every lock-ON save ever made there
is no record anywhere of how far the stored corners drifted from what the person
in front of the screen actually placed. On a synthetic test quad that drift is
**0.508 px**; on a hand-dragged quad it can be far larger, and it was invisible.

---

## 2. What changed in the code

### `tools/court_setup_server.py`

Three new module-level functions (module-level so they are testable without a
socket; the save logic previously lived entirely inside a request-handler
closure):

| function | purpose |
| --- | --- |
| `provenance_block(state, shape_lock, moved_px)` | builds the `_provenance` dict |
| `source_desc(args)` | describes what frame the corners were placed on, or admits it cannot know |
| `save_text(named, exact, provenance=None)` | the single writer for both save paths |

Both `/api/save` branches now write through `save_text`. `state["source"]` is set
in `select_clip()` (gallery) and in all three `state = {...}` constructions in
`main()` (camera, video/frame/clip).

### The `_provenance` field names

```json
"_provenance": {
  "placed_by": "unattributed",
  "tool": "tools/court_setup_server.py",
  "shape_lock": true,
  "moved_px": 0.5083531272432631,
  "saved_at": "2026-09-09T02:24:21+00:00",
  "source": {"kind": "gallery_image", "path": "data/gold/frames/x/0007.jpg"}
}
```

| field | meaning | why it is shaped this way |
| --- | --- | --- |
| `placed_by` | always `"unattributed"` on save | The tool **cannot know**. This is a slot for a human or a commit to fill in, not a claim. It is deliberately not `"human"`, not `"user"`, and not blank — a blank invites the same optimistic reading that sank `_exact`. **Do not read `"unattributed"` as "human".** |
| `tool` | `"tools/court_setup_server.py"` | Distinguishes a setup-tool save from a file written by a script or by hand. |
| `shape_lock` | `true` = corners were solved by `lock_shape()`; `false` = stored exactly as placed | This is the *fact* `_exact` was standing in for. `_exact` is still written (the pipeline reads it) but is now no longer the only record. |
| `moved_px` | the value `lock_shape()` computes and previously discarded | **The important one.** How far the solver shifted the placement it was given. `0.0` by definition on the lock-OFF path. |
| `saved_at` | UTC ISO-8601, second resolution | Groups a save session without needing a commit. |
| `source` | `{kind, ...}` — see below | Frame identity where the tool genuinely has it. |

`source.kind` is one of: `gallery_image` (has an exact `path` — gallery is the one
mode that knows which image is on screen), `image` (`--frame`), `video_clean_plate`
or `video_single_frame` (`--video`), `gold_clip_middle_frame` (`--clip`),
`live_camera` (`--camera`), `unknown`.

For every kind except `gallery_image` and `image`, `frame` is explicitly `null`
with a `note` saying why. `--video` in particular calibrates on a **temporal
median clean plate over ~80 frames** — there is no single source frame, and
recording a frame index would be an invention. Saying so is the point of the
field.

`_provenance` is underscore-prefixed, so all 17 consumers in `backend/`, `tools/`
and `eval/` skip it via their existing `if not k.startswith("_")` filter (grepped;
`backend/swingvision/pipeline.py:439`, `calibration.py:686`, and 15 others).

### `eval/run_refs.py`

- The false docstring claim is replaced with what `_exact` actually means, plus a
  note that it is how agent placements entered the pool.
- `references()` now prints a provenance warning **to stderr**, once per process,
  before returning. It warns from inside `references()` rather than `main()`
  because eight other eval scripts import `references()` directly and the point is
  that nobody scores against this pool without seeing the caveat. stderr so it
  cannot corrupt a parsed stdout table.
- `CORNER_SOURCE_COMMIT` maps each pool clip to the commit that last wrote its
  corner numbers. A clip missing from the map prints as `unknown`, never as clean.

Live output:

```
!! PROVENANCE WARNING - these references are NOT verified human placements.
   `_exact` only means the Shape-lock box was unticked at Save; it records
   nothing about who placed the corners (docs/evidence/calibration-provenance.md).
   6/20 clips had their corner values written by 3399d58 or ac94aab:
     A7vXlWIlyrI, HoHxFSX_gLk_s1, UHf0LeMU2pg, e8T34KoJzOw_s2, tc8CGFxyRE8, uR5q2cSM6AY
   9/20 come from the wider 2026-08-11/12 agent
   calibration session (6a3e10f, 63f304e, 8c29896, 209b6b5, 1b3f623, 3399d58, ac94aab), ...
```

---

## 3. PRE-REGISTERED CHECK — result

**Pre-registered:** `eval/run_refs.py::references()` must return the identical set
of clips before and after the change.

**Result: PASS.** Captured before any file was touched, re-captured after all
edits, diffed: **byte-identical, 20 clips, same order, same paths.**

```
A7vXlWIlyrI  am_hard_utr  CYqapSq5llo  e8T34KoJzOw_s2  flexi_franz_p01
flexi_franz_p07  flexi_joy_p01  flexi_joy_p07  hillsborough_p02
hillsborough_p08  HoHxFSX_gLk_s1  HoHxFSX_gLk_s2  mpc_mixed_p02  mpc_mixed_p08
mpc_tuesday_p01  mpc_tuesday_p07  sAjkpeRq4P4  tc8CGFxyRE8  UHf0LeMU2pg
uR5q2cSM6AY
```

Which clips are scored did not move. Only what may be *claimed* about them did.

---

## 4. Corners unchanged — the rule-8 proof

`backend/tests/test_court_setup_save_provenance.py`, **12 tests, all pass**
(full suite: **605 passed**). Three claims, weakest dependency first:

1. **Structural, machine-independent.** Take the new file, drop `_provenance`,
   re-dump with the same options — you get the pre-change text back character for
   character. Holds for *any* corner values, so it does not depend on this
   machine's optimiser arithmetic. A companion test pins that `_exact` and
   `_provenance` are appended **after** the four corners; a key inserted ahead of
   them would reflow their serialised text.
2. **End-to-end, self-consistent.** The test starts the real `ThreadingHTTPServer`
   on port 0 and POSTs to `/api/save` on **both** paths, then asserts the corners
   on disk are byte-identical (`json.dumps` compared as strings) to the corners
   the handler reported in its own reply. This pins that `save_text` writes exactly
   what `lock_shape` returned, with no rounding or reordering in between.
3. **Golden.** For one fixed 1280×720 placement, the lock-ON corners produced by
   the **pre-change** code (at `d4fb85b`) are embedded in the test:

   ```
   near_bl_doubles [210.00000123933387, 690.000000668731]
   near_br_doubles [1089.9999992723165, 700.0000047979105]
   far_br_doubles  [829.9605873021665,  299.4931770119386]
   far_bl_doubles  [469.9982650203806,  296.01333126950584]
   moved_px        0.5083531272432631
   ```

   Compared with tolerance `1e-9` px rather than `==`: the shape lock is a scipy
   optimisation and its last bits are not portable across BLAS builds. More than a
   nanopixel of drift is not floating point, it is a behaviour change.

The pre-change capture was run **twice** and produced identical bytes, so the save
path is deterministic and the golden is a real pin, not a lucky draw.

---

## 5. Git provenance of every existing `*_pts*.json`

**Method — and why the obvious method is wrong.** `git log --diff-filter=A` (the
commit that *added* the file) gives the wrong answer here: several of these files
were added by one commit of the 2026-08-11 session and then **re-placed** by a
later commit of the same session. And several commits touch a `_pts.json` without
moving a corner at all — they only stamp `_audit`.

So the table below is built by parsing every historical version of every file,
dropping all underscore-prefixed keys, and comparing the four corner values
against the same file in the commit's first parent. A commit is credited with the
placement **only if the numbers changed**. Reproduce with:

```
for each tracked data/*_pts*.json:
  for each commit in `git log --format=%h -- <file>`:
     compare {k: v for k, v in json(git show <sha>:<file>) if not k.startswith("_")}
     against the same dict at `git rev-list --parents -n 1 <sha>`'s first parent
```

`_audit`-only touches are listed separately so they cannot be mistaken for
re-placements.

### 5a. The 20 clips in the scoring pool

| clip | `_exact` | first wrote corners | **LAST wrote corners** | metadata-only touches |
| --- | --- | --- | --- | --- |
| A7vXlWIlyrI | yes | 6a3e10f 08-11 | **3399d58** 08-11 | 1b3f623 |
| CYqapSq5llo | yes | 6a3e10f 08-11 | **6a3e10f** 08-11 | 1b3f623 |
| HoHxFSX_gLk_s1 | yes | 6a3e10f 08-11 | **3399d58** 08-11 | 1b3f623 |
| HoHxFSX_gLk_s2 | yes | 1b3f623 08-11 | **1b3f623** 08-11 | — |
| e8T34KoJzOw_s2 | yes | 6a3e10f 08-11 | **3399d58** 08-11 | 1b3f623 |
| tc8CGFxyRE8 | yes | 63f304e 08-11 | **3399d58** 08-11 | 1b3f623 |
| UHf0LeMU2pg | yes | 8c29896 08-11 | **3399d58** 08-11 | ac94aab, 1b3f623 |
| uR5q2cSM6AY | yes | 8c29896 08-11 | **3399d58** 08-11 | ac94aab, 1b3f623 |
| sAjkpeRq4P4 | yes | 209b6b5 08-11 | **209b6b5** 08-11 | ac94aab, 1b3f623 |
| am_hard_utr | yes | d3f84af 07-28 | **d3f84af** 07-28 | 20a672e |
| flexi_franz_p01 | yes | 7c8b8af 08-26 | **7c8b8af** 08-26 | — |
| flexi_franz_p07 | yes | 7c8b8af 08-26 | **7c8b8af** 08-26 | — |
| flexi_joy_p01 | yes | 7c8b8af 08-26 | **7c8b8af** 08-26 | — |
| flexi_joy_p07 | yes | 7c8b8af 08-26 | **7c8b8af** 08-26 | — |
| hillsborough_p02 | yes | 7c8b8af 08-26 | **7c8b8af** 08-26 | — |
| hillsborough_p08 | yes | 7c8b8af 08-26 | **7c8b8af** 08-26 | — |
| mpc_mixed_p02 | yes | 7c8b8af 08-26 | **7c8b8af** 08-26 | — |
| mpc_mixed_p08 | yes | 7c8b8af 08-26 | **7c8b8af** 08-26 | — |
| mpc_tuesday_p01 | yes | 7c8b8af 08-26 | **7c8b8af** 08-26 | — |
| mpc_tuesday_p07 | yes | 7c8b8af 08-26 | **7c8b8af** 08-26 | — |

### 5b. Everything else tracked under `data/`

| file | `_exact` | first wrote corners | **LAST wrote corners** | metadata-only touches |
| --- | --- | --- | --- | --- |
| HoHxFSX_gLk_s3_pts.json | no | 3399d58 08-11 | **3399d58** 08-11 | 3147d7f |
| L73ep7JHiJ4_pts.json | no | ac94aab 08-12 | **ac94aab** 08-12 | — |
| eala_pts_auto.json | no | 6aeeb20 07-07 | **6aeeb20** 07-07 | 20a672e |
| demo30_pts.json | no | e223d40 07-05 | **5f1a457** 08-03 | 20a672e |
| yt_match40_pts.json | no | e223d40 07-05 | **11044fc** 09-05 | 20a672e |
| court_pts.json | no | e223d40 07-05 | **e223d40** 07-05 | 65a5086, 20a672e |
| court_pts_refined.json | no | e223d40 07-05 | **e223d40** 07-05 | 20a672e |
| yt_court_pts.json | no | e223d40 07-05 | **e223d40** 07-05 | 20a672e |
| yt_court_pts_doubles.json | no | e223d40 07-05 | **e223d40** 07-05 | 20a672e |
| yt_court_pts_refined.json | no | e223d40 07-05 | **e223d40** 07-05 | 20a672e |
| yt_court_pts_singles.json | no | e223d40 07-05 | **e223d40** 07-05 | 20a672e |
| yt_rally2_pts.json | no | e223d40 07-05 | **e223d40** 07-05 | 65a5086, 20a672e |

`data/yt_match40_pts.json.bak-2026-09-05` is tracked but is a backup, not a
reference; nothing reads it.

---

## 6. The count the brief expected, and the count the evidence gives

The brief stated that **9 of the 20** pool clips came from `3399d58` or `ac94aab`.
Measured against corner values, that is **not what those two commits did**:

- **`3399d58`** last wrote the corner values of **6** pool clips: `A7vXlWIlyrI`,
  `HoHxFSX_gLk_s1`, `e8T34KoJzOw_s2`, `tc8CGFxyRE8`, `UHf0LeMU2pg`, `uR5q2cSM6AY`.
  (It also wrote `HoHxFSX_gLk_s3`, which is not `_exact` and not in the pool — so
  the "ten hand-placed calibrations" of its subject line map to 7 files here.)
- **`ac94aab`** wrote corner values for exactly **one** file, `L73ep7JHiJ4_pts.json`,
  which is **not** `_exact` and **not** in the pool. For `UHf0LeMU2pg`,
  `uR5q2cSM6AY` and `sAjkpeRq4P4` it is a **metadata-only** `_audit` stamp. It
  contributes **zero** pool clips.

So "3399d58 or ac94aab" = **6 by value, 7 by any touch**. Not 9.

**The founder's 9 is nonetheless correct — under the right unit.** The two named
commits are two of **seven** commits in one continuous agent calibration session
on 2026-08-11/12:

```
6a3e10f  Do not hand the labeller a smeared plate when the camera moves
63f304e  One browser tab for the whole calibration queue, not one per clip
8c29896  Stop the calibration queue debugging itself blind
209b6b5  Build every clean plate up front so the queue stops stalling
1b3f623  One page, every court, click to switch
3399d58  Ten hand-placed court calibrations for the new training pool
ac94aab  The exam set grows from six clips to ten
```

Every one of these is a commit in which an agent was *building and driving the
calibration tool on itself*. Counting the session, **exactly 9 of the 20 pool
clips** have their corner values written by it — the 6 above plus `CYqapSq5llo`
(6a3e10f), `HoHxFSX_gLk_s2` (1b3f623) and `sAjkpeRq4P4` (209b6b5). That is the
founder's number, and it reproduces exactly.

**`3399d58` is the session's closing commit, not its only one.** Anyone auditing
this by commit hash alone will under-count by a third. `eval/run_refs.py` now
prints both figures for that reason.

### The third batch the brief does not mention

The remaining 11 pool clips are **10 shell clips from `7c8b8af`** (2026-08-26,
*"Ten human court calibrations for the five indoor shell venues"*) plus
`am_hard_utr` from `d3f84af` (2026-07-28).

`7c8b8af` is **half the scoring pool** and its subject line asserts "human" with
**no evidence inside any of the ten files**. It has exactly the same evidentiary
status as `3399d58`'s claim: a commit message written in the first person. It may
well be genuinely human — but that is currently an assumption, and it is the
single largest unverified block in the pool. The founder's review of the rendered
sheets covers these clips and is the only instrument that can settle it.

### Corroboration that the batch judged itself

`3399d58`'s own message claims *"all 10 were verified by eye with the court
projected back onto the frame"* and, in the same message, retracts two of its own
verdicts: *"RETRACTED: I reported uR5q2cSM6AY (9.3 px) and HoHxFSX_gLk_s2 (1.0 px)
as misplaced. Both are correct. I judged them from 560-px thumbnails."* One agent
placed the corners and was the sole judge of the placement, and its visual verdict
flip-flopped once **inside a single commit message**. Both retracted clips are in
the pool today.

Note also `8c29896`, *"Stop the calibration queue debugging itself blind"* — the
session was aware of the self-verification problem at the time and fixed the
tooling, not the epistemics.

---

## 7. Gaps this record does not close

- **3 of the 28 rendered corner sheets have no matching `*_pts.json` in the repo**:
  `bump_ntrp30`, `bump_ntrp30b`, `eala_segment`. Their placements cannot be traced
  by this method. Not investigated further — out of scope for this task.
- **The founder's specific list of 10 wrong sheets was not available to me**, so
  this document cannot cross-tabulate "flagged wrong" against "commit". Once that
  list exists, section 5a is the join key. That table is the reason to keep it.
- **No existing file was backfilled** and no corner value was touched. The
  `_provenance` block appears only on saves made from 2026-09-09 onward. Every
  file in section 5 is therefore still provenance-blind in-file; git plus this
  document is its only record.
- **`placed_by` will read `"unattributed"` for agent and human alike.** This change
  removes a *false* signal; it does not create a true one. Genuine attribution
  needs either a human typing their name into the tool or a policy that human
  placements are committed separately and labelled in the commit — a product/process
  decision, not a code one. Escalated to pm, not decided here.

---

## Files touched

- `tools/court_setup_server.py` — `provenance_block`, `source_desc`, `save_text`;
  both `/api/save` paths; `state["source"]` in `select_clip` and all three
  `state = {...}` constructions; `datetime` import.
- `eval/run_refs.py` — corrected docstring, `CORNER_SOURCE_COMMIT`,
  `FLAGGED_COMMITS`, `FLAGGED_SESSION`, `provenance_warning()`, stderr warning in
  `references()`.
- `backend/tests/test_court_setup_save_provenance.py` — new, 12 tests.

---

# 8. Addendum, same day — three defects in the AUDIT INSTRUMENTS

The sections above are about how bad ground truth got in. This section is about
the tools that render the sheets the founder is re-reviewing it with. **An audit
instrument's failure modes are findings, not chores**: a defect here corrupts the
re-review the same way self-verification corrupted the original placement, and it
does so invisibly, because the output of a broken renderer looks exactly like the
output of a working one.

For each defect: what it was, what was done, and — the part that matters — **what
it could have hidden.**

## 8.1 `--tag` was accepted and silently ignored on the corner path

`main()` passed `args.tag` only to `render_net_anchors()`. `render()` recomputed
the tag from the `*_pts.json` filename stem, so the output was always
`<stem>_corners.png` and the flag did nothing. Nothing warned.

**Fixed by making it work, not by erroring.** Two reasons. The flag has a real
use on this path — auditing a `.bak` or a variant calibration under its own name,
which `--video-tag` already supports — and rejecting it would have left the worse
half of the bug in place, since *no flag was needed to trigger it*. The output
filename now carries the frame index (`<tag>_corners_f<N>.png`), so N renders
produce N files. Passing `--tag` with more than one `--pts` file is now an
explicit error (one output name cannot serve several inputs), as is
`--post-height` without `--net-anchors`, which was the third accepted-and-ignored
flag in the same parser.

**What it could have hidden:**

1. **Silent destruction of the evidence behind a verdict.** The lead rendered one
   clip at five frame indices today: five runs, one surviving PNG, four
   overwritten with no error and no record. If a reviewer marks a sheet "wrong"
   and the sheet is later overwritten by a re-render, the artifact backing that
   judgement no longer exists and the judgement cannot be re-checked — the exact
   chain-of-custody failure T26 is about, one layer downstream.
2. **A DISAGREEMENT BETWEEN FRAMES, erased.** Render frame A, render frame B, keep
   only B. If the corners fit at A and not at B, that difference *is* the camera
   motion finding (§8.2) — and the file layout guaranteed only one of the two
   survived, silently and always the last one.
3. **A variant calibration wearing the canonical clip's filename.** Rendering
   `foo_pts.json.bak` produced `foo_corners.png` — a sheet that does not say, in
   its own name or caption, which file it depicts. A reviewer would have been
   auditing a backup while believing they were auditing the shipped calibration.
   `index.json` recorded only the output name, so nothing could have caught it.

## 8.2 It rendered frame 0; the evaluation scores frames 5%–95%

`eval/run_refs.py::frames_from` samples `k=8` frames evenly across 5%–95% of the
clip. `render_corner_audit.py` defaulted to `--frame 0`. **All 28 sheets the
founder reviewed were frame-0 sheets.**

**The default is now one of the eval's own eight samples** — the lower-middle one
— obtained by importing the newly extracted `run_refs.frame_positions(total, k)`
rather than copying the formula, because a copied formula is how the two drifted
apart in the first place. `frames_from` now calls that same function; the
refactor is pinned by `backend/tests/test_eval_frame_positions.py`, which
reproduces the old inline expression verbatim and asserts equality across 14
frame counts × 6 values of `k` (repo rule 8). The frame is fetched with the same
`CAP_PROP_POS_FRAMES` seek `frames_from` uses, so if the decoder lands somewhere
other than the nominal index it lands there for both.

**The ONE-vs-EIGHT mismatch is stated, not papered over.** The caption now reads
`frame 12634 = eval sample 4/8 (run_refs, 5%–95% of 28998)` on its top line and,
underneath, *"ONE frame shown; run_refs scores EIGHT. A single frame cannot show
camera motion — `--eval-frames` renders all 8."* `--eval-frames` is new and does
exactly that, writing eight separately-named sheets. A single image cannot
establish that a camera never moved, and no default can fix that; the fix is that
the sheet now says so and offers the eight.

**What it could have hidden — in BOTH directions, which is why it is not cosmetic:**

1. **A false ACQUITTAL.** Corners can sit perfectly on the lines at frame 0 and be
   far off across the entire scored band if the camera pans, is bumped, or zooms.
   That calibration passes a human's eye and still scores as a wrong court in
   `run_refs`, and the two results look like a mystery rather than a mismatch.
2. **A false ACCUSATION — the live risk today.** The founder marked **10 of 28**
   sheets wrong-placed from frame-0 renders. `tools/court_setup_server.py` places
   corners against frame 0 only in `--video` mode (`cap.read()` once, line 121);
   in gallery mode the image comes from `eval/collect_frames.py`, which seeks to
   arbitrary positions across the clip (`CAP_PROP_POS_FRAMES`, and it records the
   real landing position). **So for every gallery-placed calibration the sheet was
   rendered at a frame that is not the frame the corners were placed against**, and
   on a clip with any camera motion a correct placement is displayed as a wrong
   one. That would remove a *good* calibration from the pool while the re-review
   believed it was removing a bad one.
3. **Which of those two applies is currently unknowable per clip.** Nothing in a
   `*_pts.json` records whether the camera moves, or which frame the corners were
   placed against. Saves from 2026-09-09 carry `_provenance.source` (§4), which
   fixes the second half going forward and nothing retroactively. **Camera motion
   remains unrecorded anywhere** — `--eval-frames` is the only instrument for it,
   and it is a human-eye instrument, not a number.
4. **Frame 0 is also the least representative frame available**: pre-play, often a
   walk-on, a title card, or the first frames of exposure/autofocus settling.
   Nothing in the tool preferred it; it was simply the cheapest sequential decode.

## 8.3 `eval/candidate_audit.py` still claimed UNRUN

Its header said *"UNRUN. No number in this repo has been produced by it yet."* It
has run at least twice. Corrected from git and from the artifacts that consumed
it, never from prose:

| Run | Evidence |
| --- | --- |
| 2026-08-26, 10 refs × 8 frames | `data/output/candidate_audit.json` — **committed in `424ecdc`, the same commit that introduced the script.** Consumed by `data/output/court_scoring_diagnosis.md` §10 and `docs/evidence/indoor-shell-courts.md` (shell 3/10). `--movers` ran the same day → `docs/evidence/far-player-motion-gate-result.md` |
| 2026-09-09, full 20-clip pool | `docs/evidence/candidate-proposal-recall.md`, published in `5e322e2` (proposal recall 40%; shell 2/10) |

`git log` on the script itself proves none of this — it has been edited once since
creation. **A script's run history lives in its outputs' commits, not its own.**
The corrected header also carries the two caveats a reader of "UNRUN" had no
reason to look for: `truth_would_pass = 9/20` is not quotable (all-or-nothing over
8 frames; it self-contradicts on 5 of 8 clips), and every number it produces is
scored against the human courts now under review.

**What it could have hidden:**

1. **It already cost a wrong draft.** qa drafted "both stages are broken" on
   2026-09-09 and retracted it in place after finding the prior Session O results
   the docstring said did not exist.
2. **It destroys the A/B by hiding the first arm.** Shell proposal recall moved
   **3/10 → 2/10** between the two runs. Because the first run was believed not to
   exist, no per-clip record was kept to compare against, so a possible regression
   (the `4a33635` refiner-reach scaling, cleared on a 12/20 gate that contains no
   4K shell clip) is **unconfirmable rather than confirmed or refuted**. That is
   the specific, permanent cost.
3. **It launders a re-run as a first measurement.** "UNRUN" invites running with
   different parameters and quoting the result as *the* number, with no prompt to
   diff it against the earlier one.

**This is trap T24 for the second time** (`eval/movers.py` carried the identical
false claim while two `docs/STATE.md` rows already quoted its output). The habit
that catches it, from qa's memory: *before running any eval script in this repo,
grep `docs/evidence/` and `data/output/` for its numbers.*

## 8.4 What did NOT change

No corner value was read, written or re-placed (repo rule 9 — the founder owns
that). `eval/run_refs.py::references()` returns the same clips; only the frame
positions were extracted into a named function, and `frames_from` returns exactly
what it returned before (pinned by test). Full suite **693 passed** after the
change (605 before + 88 new parametrised cases).

**A consequence to state before someone reports it as a regression:** every
published `--net-anchors` number (`docs/evidence/net-anchor-calibration-check.md`,
`data/output/corner_audit/net_index.json`, the tape 13/15 and post 3/11 tallies)
was measured at **frame 0**, because that was the default. Re-running now measures
a mid-clip frame, and `band_ratio` / `dy_best` are frame-dependent quantities — a
different value is a different frame, not a changed result. **Pass `--frame 0` to
reproduce the published table.** One variable per A/B (rule 7) applies to the
frame index too.

**Not fixed, and worth naming:** the existing 28 sheets in
`data/output/corner_audit/` are still frame-0 renders under the old
`<tag>_corners.png` names. They are not deleted and nothing renames them — but a
re-review that mixes them with new `_f<N>` sheets is comparing two different
frames of the same clip. Re-render before re-reviewing.

## Files touched (addendum)

- `tools/render_corner_audit.py` — `--tag` honoured on the corner path;
  `--eval-frames`; `--frame` default now the eval's sample; `eval_positions`,
  `frame_count`, `default_frame`, `grab_frame(seek=)`; frame index in both output
  filenames and in `index.json` / `net_index.json`; caption states the frame and
  how it was chosen; three refused flag combinations.
- `eval/run_refs.py` — `frame_positions(total, k)` extracted from `frames_from`.
- `eval/candidate_audit.py` — docstring run history corrected (docstring only; no
  behaviour change).
- `backend/tests/test_eval_frame_positions.py` — new, 88 cases.
