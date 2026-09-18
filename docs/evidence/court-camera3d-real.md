# The 3D court camera on REAL footage: lock, agreement, repeatability, tracking

**2026-09-18, founder instruction: "Test and learn on real footage."**

- Tool: `tools/court_real_probe.py`.
- Clips: the strict-16 references pool (`eval/run_refs.references()`), with the videos hard-linked
  from the main repository's `data/incoming` (git-ignored here). The pool is:
  - 10 indoor-shell tripod clips at 3840×2160 / 30 fps;
  - `am_hard_utr`, `e8T34KoJzOw_s2`, `tc8CGFxyRE8` and `uR5q2cSM6AY` (hard court, 1080p);
  - `sAjkpeRq4P4` and `CYqapSq5llo` (clay, 1080p).
- Code under test: `camera3d.fit_camera_checked` (paint fit + per-line paint check + dolly/alley
  restarts) and `camtrack.CameraTracker` (paint-checked tracker). Both were developed on
  synthetic seeds only (`court-camera3d.md`); neither has a scored synthetic gate yet.

## WHAT THIS CAN AND CANNOT MEASURE

**No clip has metric truth** (no court visit). **Nothing here is an accuracy number.** Each figure
says what it was measured against:

| Quantity | Measured against | What it can show |
|---|---|---|
| **lock** | the image: `paint_check` on the fitted camera (every checkable line on paint) | whether the fit found the court's paint; not where the far lines are (they are too thin to check) |
| **vs_human** | the four doubles corners in `data/<clip>_pts.json`, px@640 | **agreement** with a placement whose click spread is ~5.8 px@640 and which is contested on 5/16 clips (the agent calibration session, `calibration-provenance.md`) |
| **repeat** | the fit from the clean human seed | whether a noisy seed (σ 14.78 px@1080, 5 draws) returns to the **same** camera; repeatability, not accuracy |
| **track** | the tracker's own camera at the first frame | the lock fraction, and how far the tracked court moves in the image; meaningful only where the camera is believed static (the shell tripods measured 0.1–0.4 px@640 background motion, `camera-motion-vs-court-agreement.md`) |
| **courtnet** | the human-seeded fit | whether an AUTOMATIC seed (`CourtNetKeypoints`, `courtnet_split.pt`) reaches the same camera |

**Leak check, name-only:** `courtnet_split.pt`'s training clips (`data/gold/court_split.json`)
are `am_*` gold clips plus `highangle`, `indoor_elev` and `indoor_low`. No pool clip appears by
name. Where those three came from is not recorded here, so the check is by name only.

**The human corners are a SEED, never a precision input** (founder ruling). In the product,
a detector supplies the seed; the human seed here isolates the fit from detection.

**Setup:**
- Frames: 30 consecutive frames starting at the eval's sample 4 of 8, averaged.
- 4K frames are downscaled to 1920×1080, the resolution the paint fit was measured at.
- Tracking runs for up to 180 frames from the same start.
- Real phone and YouTube compression is in every frame.

**Development before pre-registration:** two clips outside the pool, `L73ep7JHiJ4` and
`HoHxFSX_gLk_s2`, used only to debug the tool. Their numbers are reported below as development,
not results.

---

## PRE-REGISTRATION — committed before the first pool run

These are **operational expectations** for a first real-footage look, labelled as such. They are
not SPEC bars.

- **E1 LOCK.** The human-seeded fit passes the paint check on **≥ 12 of 16** clips.
  - Prediction: shell is the risk (roof trusses and lights). On the 1080p clips, compression and
    worn paint are the risk.
- **E2 AGREEMENT.** On the clips that lock, the median (over clips) of each clip's median corner
  disagreement with the human clicks is **≤ 10 px@640**. This is twice the human click spread,
  because both sides carry error.
- **E3 REPEAT.** On the clips that lock, **≥ 4 of 5** noisy seeds return within **5 cm** (worst
  line) of the clean-seed camera, on **≥ 75%** of those clips.
- **E4 TRACK (shell tripods only).** On the shell clips that lock:
  - tracker lock fraction **≥ 0.90**;
  - the court moves **≤ 2 px@1080** in the image over the clip.

  On the 1080p clips the camera may move (edited YouTube), so tracking there is **reported, not
  gated**.
- **E5 COURTNET.** Reported, no gate. **Prediction: ≤ 3 of 16** clips reach within 5 cm of the
  human-seeded camera. The upstream checkpoint fires on 2–3 of 14 keypoints on amateur footage
  (`cnn-global-classical-local.md`), and PnP needs 5.

**KILL for this route on real footage:** E1 below **8 of 16**. That would mean the paint fit does
not survive real images, whatever it does on renders.

Every contact image (`<clip>_fit.jpg`: fitted court and human corners) is written for a human
eye, **including the rejects** (rule 9).

---

## Development (not results)

*(filled in from the development run)*

## Results

*(filled in after the pool run; bars above not moved)*
