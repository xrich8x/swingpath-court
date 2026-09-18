---
name: tracker-fixes-hold-on-held-out-seeds
description: The post-G3 camtrack fixes reproduce on their dev seeds AND improve on fresh seeds, so they are not seed-tuned — but they stay UNSCORED and still produce a confident wrong lock on the far lines
metadata:
  type: project
---

**Measured 2026-09-18 by re-running `tools/court_track_sim.py` myself** (120 frames/seed, against the
exact synthetic camera that rendered each frame). Committed in `1f377af`.

| Run | worst line p90 | steady jump | knock recovery | locked / locked-wrong / unlocked |
|---|---|---|---|---|
| dev seeds 100-102 (the quoted seeds) | 3.52 cm | 0.18 px | 1,1,1 | 358 / 1 / 2 |
| **fresh seeds 200-202** | **2.41 cm** | 0.18 px | 1,1,1 | 358 / 1 / 2 |
| fresh seeds, knock x4 | 198.8 m KILL | 1.93 px | never x3 | 180 / 0 / 180 |

**Why this mattered:** `camtrack.TrackConfig` admits in a comment that `q_rot`/`q_pos` were moved
1e-2 -> 100 on "dev seed 100", one of the three seeds the 3.5 cm is quoted against. The suspicion was
well founded; the answer is that the fixes generalise anyway.

**How to apply:**

- **Running the quoted seeds AND fresh seeds is the cheap, decisive test for seed-tuning.** ~3 min
  per seed here. Do it before writing "tuned on its own dev data" in a report.
- **Generalising is not passing.** There is no pre-registered gate for the fixed tracker; G3's gate
  was pre-registered and failed, and a failed gate stays failed. The sim prints "PASS" against C1's
  5 cm bar on its own — that string is not a gate. Status stays UNSCORED.
- **The confident wrong lock survives the fix.** Seed 101 frame 60 and seed 201 frame 60 both report
  `locked=True, status=tracking` at 70.4 cm / 56.8 cm worst line, concentrated in `far_baseline` and
  `far_service` — exactly the two lines `paint_check` marks `unchecked`. See [[g7-separation-audit]].
- The dev numbers live **only** in `.claude/journals/lead.md`, not in any evidence file or STATE row,
  so the project record was not overclaiming. Check the journal before assuming a claim was published.
