---
name: two-court-pools-only-one-compromised
description: The court GOLD pool (the 12/20 gate) and the _exact REFERENCES pool are different artefacts; T26 compromises only the references, and only 2 of its 20 clips are confirmed misplaced
metadata:
  type: project
---

There are **two** court truth pools in this repo and they are routinely conflated, including
once in `docs/STATE.md`.

| | REFERENCES | GOLD |
|---|---|---|
| files | `data/<clip>_pts.json` with `"_exact": true` | `data/gold/*.court.labels.json` |
| selector | `eval/run_refs.py::references()` | `eval/run_eval.py --gold --all --k 8` |
| clips | `A7vXlWIlyrI`, `CYqapSq5llo`, `HoHxFSX_gLk_s1/s2`, `e8T34KoJzOw_s2`, `tc8CGFxyRE8`, `UHf0LeMU2pg`, `uR5q2cSM6AY`, `sAjkpeRq4P4`, `am_hard_utr`, 10x `flexi_*`/`hillsborough_*`/`mpc_*` | `am_classB`, `am_college`, `am_fr_sud`, `am_grass1`, `am_ntrp30`, `am_ntrp40`, `am_ntrp45_courtlevel`, `am_rally32short`, `am_rec30`, `am_usta40`, `am_usta45`, `am_usta60` (+8 refused) |
| width | 1920 / 3840 | all exactly 640 |
| placed with | `tools/court_setup_server.py` | the Lab's court labelling tool |
| what it scores | reference error, proposal recall | **the pre-registered >=12/20, zero-over-20-px gate** |

**T26 (`_exact` never meant "a human placed this") is a defect in the REFERENCES pool only.**
STATE's provenance row lists "the 12/20 gate" among the numbers inheriting it — that is
**not established**, and I flagged it to the lead rather than editing STATE.

**Why:** the gate is the only pre-registered court gate in the project and has already killed
two changes. Conflating the pools makes the damage look total when it is localised — and
makes the one genuinely unexamined thing (the gold pool has NEVER had a court rendered onto
its frame; `render_corner_audit.py` reads `*_pts.json`) invisible.

**How to apply:** before agreeing that a court number is compromised, ask which pool it was
scored against. Say "references" or "gold", never "the pool". If someone proposes re-running
court work, the first session is the gold pool's own git archaeology, not a re-measurement.

**The number that resizes the problem:** joining the 2026-09-09 re-review (4 MISPLACED,
5 MIXED, 1 HOLDS) against `run_refs.py`'s 20-clip map, **only 2 of 20 pool clips are
confirmed misplaced** — `HoHxFSX_gLk_s3` is not `_exact` and `bump_ntrp30` has no
`*_pts.json` in the repo at all. Consequence: proposal recall 8/20 = 40% could rise to at
most 10/20 = 50%, still inside the pre-registered "search binds at <=60%" band. **The SEARCH
BINDS verdict survives any reasonable correction.**

Detail: `docs/evidence/court-triage-2026-09-09.md` §B.0-B.2. Related:
[[v1-cut-line-after-court-closure]], [[cheap-tests-that-close-a-line]].
