---
name: references-pool-is-strict-16
description: The court references pool is 16 clips (was 20) since the founder's 2026-09-09 strict one-setup ruling; three different "20"s exist in this repo and only one moved
metadata:
  type: project
---

`eval/run_refs.references()` returns **16** clips, not 20, since the founder's
2026-09-09 ruling. Dropped: `A7vXlWIlyrI`, `HoHxFSX_gLk_s1`, `HoHxFSX_gLk_s2`,
`UHf0LeMU2pg`. `uR5q2cSM6AY` is a marginal fifth, **RETAINED and flagged** — do not
widen the rule to catch it without a new ruling.

**Why:** qa's ORB/RANSAC "same camera setup" edge only proves a *registrable*
background, so a hard pan-and-zoom passes it — `A7vXlWIlyrI` scored 8/8 while moving
188.3 px@640 with a 40% zoom. The strict rule adds the project's existing
`WRONG_PX_640 = 20.0` (qa's `S20`), no new constant. Second reason: the four are
edited YouTube with cuts and zooms, and the product's footage is one continuous take.

**How to apply:**
- **Every `/20` scored against the references pool is STALE, not wrong.** The list —
  file, row, published number, whether the drop moves it — is
  `docs/evidence/pool-strict-16.md`. Read it before quoting any court figure.
- **There are three different "20"s.** The `data/gold/*.court.labels.json` gold pool
  (`am_*` names, 640 wide, the **12/20 gate**) is a *different* truth set and did NOT
  move. The ball gold clips `gold_UHf0LeMU2pg` / `gold_uR5q2cSM6AY` are a third pool —
  the shared basename is a live trap. Only the references pool changed. See
  [[courtnet-weights-silently-substitute]].
- **All four dropped clips are 1920 hardcourt.** The pool lost 20% of its clips but
  **40% of its non-shell half** (10 → 6); shell rose to 62.5%. Surface-split figures
  move far more than a headline count suggests. All shell figures are untouched.
- **The pool now contains zero confirmed-misplaced clips — because the contested ones
  left, not because anything was re-placed.** The strict ruling does not resolve the
  T26 provenance problem ([[court-gold-provenance-is-unattributed]]).
- Populations enumerated by globbing calibrations directly (the 28-clip net-tape /
  net-post / setup-criterion sweeps) do **not** call `references()` and are unaffected;
  the ruling deletes no file.

**Never implement a pool exclusion by moving files.** `references()` globs
`data/*_pts*.json` **non-recursively**; `bump_ntrp30`/`b` sat in `data/amateur_clips/`
and were invisible to every measurement for weeks. The exclusion lives in
`run_refs.EXCLUDED_CLIPS` with a per-clip reason, and
`backend/tests/test_refs_pool_strict16.py` fails if the pool drifts or if the four
`*_pts.json` stop being on disk.
