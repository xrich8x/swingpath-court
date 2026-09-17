# Modules — the court feature

> Scoped to the court feature 2026-09-17. The previous module guide (ball, live calls, the Lab,
> mobile, performance) is archived at `swingpath:docs/archive/2026-09-17-pre-court-only/docs/modules.md`.

## Court code

| Where | What it does | Status |
|---|---|---|
| `backend/swingvision/court.py` | Regulation dimensions, 14 named ground landmarks, line segments, doubles alley. Mirrored to `frontend/src/lib/court.js` (numeric constants, parity-enforced). `LANDMARKS_3D` / `KEYPOINTS_3D`: 21 named 3D keypoints (the 14, the two centre marks, net-post bases and tops at 1.07 m, net centre at 0.914 m); `COLLINEAR_SETS` for the cross-ratio gate. Python-only, like `LANDMARKS`. | Real |
| `backend/swingvision/camera3d.py` | **The court's 3D camera.** `CourtCamera`: K (centred principal point), R/t (OpenCV convention), lens (none / division / Brown), `project`, `ray`, `ground_point`, `ground_homography`, `to_dict` (→ `match.json` `setup.camera`), and `pinned_by` (rule 5). `solve_pnp_seed`: rough camera from named keypoints (cross-ratio gate → RANSAC SQPnP over focal candidates → joint focal refine). `fit_camera_on_paint`: THE camera, from the paint fit. | Real; see `evidence/court-camera3d.md` |
| `backend/swingvision/paintfit.py` | The R1 whole-court fit to the painted lines (lifted from CP1, image size a parameter, optional camera seed, pose-only mode). | Measured on synthetic courts (CP1) |
| `backend/swingvision/camtrack.py` | `CameraTracker`: per frame, LK flow predicts where paint points went, each is snapped onto the paint ridge, a robust pose solve (normal residuals, focal and lens held) feeds a constant-velocity Kalman filter; paint re-fit on drift or every 10 s; big-change recovery through a keypoint detector → PnP → paint fit, holding the last good camera meanwhile. Refuses `ClassicalKeypoints` (the closed search) as its recovery detector. | Measured on a synthetic sway sim; no real footage |
| `backend/swingvision/calibration.py` | Homography from landmarks, image↔court mapping, one-parameter (division-model) lens correction read off the court lines, `court_lock_step` (per-frame snap of the court onto the paint), setup grading (camera height, measurable depth, net-tape clearance). | Real; tracking precision unmeasured |
| `backend/swingvision/courtfit.py` | The old automatic court SEARCH (classical line fit + 8-frame consensus) and `CourtWatchdog`. Also the keypoint-detector seam: `KeypointSet`, `KeypointDetector`, `CourtNetKeypoints` (every heatmap peak with its value; defaults to the leak-clean `courtnet_split.pt`), `ClassicalKeypoints` (the shipped search's corners, projected), and `cross_ratio_check` (gross-outlier gate, 60 px @720). | Search CLOSED (`docs/court/CLOSED.md`); watchdog real but recovers via the closed search; the detector seam has no amateur-trained model behind it yet |
| `backend/swingvision/_courtnet.py`, `backend/train_courtnet.py` | The CourtNet keypoint CNN and its trainer (with `assert_no_court_gold_leak`). Upstream weights do not fire on amateur footage. | The amateur-trained model is the open direction |
| `backend/swingvision/setup_state.py` | Persists framing / calibration status into `match.json`, plus an optional, type-checked `camera` block (`with_camera`, `normalize_camera`). A solved camera moves neither trust axis. | Real |
| *(main repo only)* `backend/swingvision/pipeline.py` `calibrate_video`, `analyze_video` | Calibration entry point; per-frame court tracking in the offline analysis. | Offline only |
| *(main repo only)* `backend/swingvision/live.py` | The streaming path. **Uses one fixed court and never tracks it.** | Needs tracking |
| `tools/court_camera.py` `camera_from_court_corners` (lifted from the main repo's ball package) | 6-DOF camera from four corners; **field of view is an input** (default 70°). | Real |
| `tools/court_setup_server.py` | Browser overlay setup tool: drag a whole court, snap to paint. | Real (development tool) |
| `tools/court_map_ceiling.py` | C1: how precisely a four-point court places each line, on synthetic truth. | Measured |
| `tools/court_fit_cp1.py` | CP1: whole-court line fit on rendered courts (renderer, codec, arms, readouts; the fit itself now imports `swingvision.paintfit`). | Stage 1 PASS QUALIFIED |
| `tools/court_camera3d_seed.py` | Arms K / K0: CP1's scene with a keypoint → PnP seed instead of four corners. | Measured |
| `tools/court_track_sim.py` | Renders a swaying, knocked fence-mount camera and scores `camtrack` against `court_lock_step`. | Measured |
| `tools/court_camera.py` | `frame_the_court` — a synthetic camera at a chosen height, used by C1 (lifted verbatim from the main repo's `height_curve.py`). | Real |

See `docs/calibration.md` for the calibration-file audit rules.
