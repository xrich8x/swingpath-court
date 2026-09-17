# CLAUDE.md

Orientation for Claude Code. Read this file; read the others **only when the doc map sends you there.**

**This is `swingpath-court`, the court-only repository.** `swingpath:` in a path means the MAIN repository, `xrich8x/swingpath`, which holds everything archived and the full pipeline.


## SCOPE: THE COURT FEATURE ONLY (founder, 2026-09-17)

**This repo is working on ONE feature: automatic, live 3D court mapping.** Everything else — ball
detection and tracking, bounce detection, line calls, trajectory physics, speed, spin, pose, players,
occlusion, scoring, highlights, the capture-visit protocol — is **ARCHIVED** in
`swingpath:docs/archive/2026-09-17-pre-court-only/`. It is history, not instructions. **Do not work on it, do
not propose it, and do not read the archive for tasks.** Only the founder reopens anything there.
`docs/evidence/` keeps every past result as a read-only record; only court files there are live.

## What the court feature is

An iPhone app (A13+, 100% on-device, Core ML / Neural Engine) that, from one fixed camera:

1. **Finds the court AUTOMATICALLY.** Machine learning learns the court's 3D layout, locates the near
   and far lines itself, and **infers end points that are out of view** from the regulation
   dimensions — SwingVision-style. **Never design around the precision of a human tap.**
2. **Places every line precisely**, doubles alley included, as a 3D court with a solved camera.
3. **Keeps tracking the court live.** When the phone moves, the court is still there, just shaped
   differently in the image: track and re-fit it. **Never stop and ask the user to re-tap.**

Rulings are verbatim in `docs/DECISIONS_PENDING.md` and `docs/SPEC.md`.

## The one principle: learn what you can't compute, compute what you can

- **Perception (ML)** — finding the court and its lines in the image.
- **Geometry (math)** — camera solve, homography, lens model, inferring unseen lines from dimensions.
- **Logic (rules)** — tracking bookkeeping, when to re-fit.

Do NOT "ML-ify" geometry. Regulation dimensions are exact; use them as constraints, never learn them.

## Where the court work stands — read `docs/STATE.md` for the numbers

- **C1 (measured):** a court pinned from four corner points misplaces the far lines by metres unless
  those corners are right to ~0.1 px at 1080p/3 m — **whoever or whatever finds them, an ML
  model included.** So the court must be fitted to the WHOLE painted lines, not to four points.
- **Routes (researcher):** a whole-court fit to sub-pixel line measurements can plausibly reach that;
  what survives averaging is BIAS (surface flatness x10, paint-edge convention, ultra-wide
  distortion, thermal lens drift, video compression, net tape near the far baseline).
- **CP1 (stage 1, PASS QUALIFIED by qa):** that fit places every line within 5 cm p90 on a rendered 1080p/3 m court; far-line margin ~1.4 cm, one camera pose, undeclared shared assumptions.
- **Automatic finding:** the 2026-09-09 open item — a court model trained on AMATEUR low-mount
  footage — is now the founder's chosen direction. Synthetic training data from a renderer is a
  candidate lever. Each branch in `docs/court/CLOSED.md` stays dead individually.
- **Live tracking exists only offline, in the MAIN repo:** `pipeline.analyze_video` snaps the court onto the paint per
  frame (`calibration.court_lock_step`) with a watchdog (`courtfit.CourtWatchdog`); its precision is
  unmeasured and its big-change recovery calls the closed search. `live.py` does not track at all.
- **No court code runs on a phone yet.** The iOS latency harness compiled green; sideloading is
  blocked (Sideloadly -22410) — **do not reopen that without the founder.**

## Hard rules

1. **Never let a model grade its own homework.** Score only against independent truth. State in one
   sentence what every number was measured against.
2. **Pre-register the gate before running the experiment.** A failed gate stays failed.
3. **Check `docs/court/CLOSED.md` before proposing anything.** Ideas get re-proposed here.
4. **Court gold is TEST-only, one-way, enforced** (`backend/train_courtnet.py::assert_no_court_gold_leak`). Check each model.
   **Its non-corner keypoints are COMPUTED from four clicks** — never a test of line placement.
5. **A single camera does not OBSERVE depth — it IMPOSES it.** Every 3D number names what pinned it.
   A reprojection residual certifies nothing.
6. **One variable per A/B, seeded.** `--seed` on both arms; `recipe_stamp` on every checkpoint.
7. **A refactor must prove it changed nothing.** Re-run and diff, or pin with a test.
8. **Never quietly edit ground truth.** Mislabels get recorded, not fixed.
9. **Always inspect the rejects**, not what a filter kept.
10. **Truth comes from the GAME, not the VIDEO.** Never a scoreboard, HUD or burned-in graphic as
    training target, truth or tuning signal.
11. **iOS only, A13+, on-device forever.** A network dependency is a scope violation.

## Known blockers

- **No metric real-court truth.** The founder cannot do a court visit yet. Court work runs on
  synthetic truth; look for real-footage checks that need no one on site.
- **No footage meets the capture floor** (`docs/evidence/capture-floor-census.md`): mount fixity
  binds. The best clip is `sAjkpeRq4P4` (Clay, 1080p, 3.33 m, 59.94 fps).
- **The field of view is an INPUT to the 3D camera** (`tools/court_camera.py::camera_from_court_corners`, default
  70°); a 5° error costs ~40 cm. iOS gives calibration data only with distortion correction OFF.

## Commands

```bash
# Python 3.12. Windows: backend\.venv\Scripts\python.exe (CPU), .venv-train (CUDA). `python` is a broken shim.
python tools/court_setup_server.py --video clip.mp4            # court overlay setup tool
python ../tools/court_map_ceiling.py --n 400 --seed 0          # C1 (from backend/)
python -m pytest tests/                                        # from backend/
```

## Conventions

- Court constants: `backend/swingvision/court.py` -> `frontend/src/lib/court.js`, enforced by
  `tests/test_js_mirror_parity.py`. `schema.py` is the only data contract.
- One module per stage; independently testable. Add a test for any new geometry.
- Metres for real-world measurement. Every pixel threshold scales by `frame_height/720`.
- No new dependencies for what stdlib/numpy/scipy/opencv already do.

## Doc map — read the ONE that matches your task

| Task | Read |
| --- | --- |
| What the court feature must do | **`docs/SPEC.md`** |
| About to propose a change | `docs/STATE.md`, **first** |
| About to propose something that may already be dead | `docs/court/CLOSED.md` |
| The court measurements so far | `docs/evidence/court-map-ceiling.md`, `court-precision-routes.md`, `court-fit-cp1.md`, `court-map-gold.md`, `capture-floor-census.md` |
| Any model work | `ML_PRACTICES.md` (**required**), `ML_PLAYBOOK.md` |
| About to repeat a process mistake | `docs/TRAPS.md` |
| Working on court code | `docs/modules.md`, `docs/calibration.md` |
| What is waiting on the founder | `docs/DECISIONS_PENDING.md` |

**`docs/STATE.md` is the only live record of state.** A STATE entry is **one line**.

## Which doc moves with which change

| You changed | Update | Enforced by |
| --- | --- | --- |
| Any code | **`docs/STATE.md`** | `.claude/hooks/state-guard.sh` (`[no-state]` opts out) |
| `court.py` constants | the JS mirror | `test_js_mirror_parity.py` |
| A process mistake hit **twice** | `docs/TRAPS.md` | judgement |
| This file | keep it under **150 non-blank lines** | `.claude/hooks/claude-md-cap.sh` |

## The team — `tennis-team`, court work only

| Teammate | Owns (court only) | Writes code |
| --- | --- | --- |
| **pm** | Court scope, sequencing, accuracy floors | no |
| **researcher** | ML/CV for automatic court finding, line precision, lens, tracking | no |
| **backend-dev** | Court detection, fitting, tracking; the renderer; porting to iOS | yes |
| **frontend-dev** | The iPhone court setup and overlay screens, camera capture | yes |
| **qa** | Independent verification of court gates. **Never fixes** | no |

**Announce a teammate by name** and label its output. **THREE LIVE AGENTS PROJECT-WIDE**
(`.claude/hooks/agent-cap.sh`); the lead holds **one** direct child at a time. A refusal is PARKED.
A surprising RESULT goes to `researcher`, then `pm`. **Batch founder asks into ONE update.**

**`.claude/journals/` — one per agent plus `lead.md`, written DURING work.** Read yours FIRST on
restart. **A KILL IS NOT A PAUSE.** Only the founder pauses, via `lead.md`'s `RUN-STATE:`.
