# Modules — the court feature

> Scoped to the court feature 2026-09-17. The previous module guide (ball, live calls, the Lab,
> mobile, performance) is archived at `swingpath:docs/archive/2026-09-17-pre-court-only/docs/modules.md`.

## Court code

| Where | What it does | Status |
|---|---|---|
| `backend/swingvision/court.py` | Regulation dimensions, 16 named landmarks, line segments, doubles alley. Mirrored to `frontend/src/lib/court.js` (parity-enforced). | Real |
| `backend/swingvision/calibration.py` | Homography from landmarks, image↔court mapping, one-parameter (division-model) lens correction read off the court lines, `court_lock_step` (per-frame snap of the court onto the paint), setup grading (camera height, measurable depth, net-tape clearance). | Real; tracking precision unmeasured |
| `backend/swingvision/courtfit.py` | The old automatic court SEARCH (classical line fit + 8-frame consensus) and `CourtWatchdog`. | Search CLOSED (`docs/court/CLOSED.md`); watchdog real but recovers via the closed search |
| `backend/swingvision/_courtnet.py`, `backend/train_courtnet.py` | The CourtNet keypoint CNN and its trainer (with `assert_no_court_gold_leak`). Upstream weights do not fire on amateur footage. | The amateur-trained model is the open direction |
| `backend/swingvision/setup_state.py` | Persists framing / calibration status into `match.json`. | Real |
| *(main repo only)* `backend/swingvision/pipeline.py` `calibrate_video`, `analyze_video` | Calibration entry point; per-frame court tracking in the offline analysis. | Offline only |
| *(main repo only)* `backend/swingvision/live.py` | The streaming path. **Uses one fixed court and never tracks it.** | Needs tracking |
| `tools/court_camera.py` `camera_from_court_corners` (lifted from the main repo's ball package) | 6-DOF camera from four corners; **field of view is an input** (default 70°). | Real |
| `tools/court_setup_server.py` | Browser overlay setup tool: drag a whole court, snap to paint. | Real (development tool) |
| `tools/court_map_ceiling.py` | C1: how precisely a four-point court places each line, on synthetic truth. | Measured |
| `tools/court_fit_cp1.py` | CP1: whole-court line fit on rendered courts. | In progress |
| `tools/court_camera.py` | `frame_the_court` — a synthetic camera at a chosen height, used by C1 (lifted verbatim from the main repo's `height_curve.py`). | Real |

See `docs/calibration.md` for the calibration-file audit rules.
