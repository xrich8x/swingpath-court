"""court_real_video.py - the 3D court camera on a REAL clip, as a video.

REAL FOOTAGE HAS NO METRIC TRUTH here (no court visit), so this video shows what
can honestly be shown and nothing more:

  - the fitted 3D court drawn over the frame, GREEN while the independent on-paint
    check passes and RED while it does not (camera3d.paint_check - it reads the
    image at the camera's own predictions, not the points the tracker chose);
  - which lines that check could actually verify, printed on the frame: at 1080p
    the far lines are usually too thin for it, so "locked" means what it says;
  - the tracker's status and how far the court has moved in the image since the
    first frame (px), which on a tripod should be ~0;
  - the human-clicked corners, for comparison only: their own click spread is
    ~5.8 px@640 and they are contested on 5 of the 16 pool clips.

NO ERROR IN CENTIMETRES IS SHOWN, because none can be measured on this footage.

    cd backend && .venv/Scripts/python.exe ../tools/court_real_video.py --clip sAjkpeRq4P4
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "eval"))

from swingvision import camera3d, camtrack, court, paintfit   # noqa: E402

WORK = (1920, 1080)
DBL = paintfit.CORNERS


def label(img, lines, y0=44, x=14):
    for i, (txt, col) in enumerate(lines):
        y = y0 + i * 42
        cv2.putText(img, txt, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 6, cv2.LINE_AA)
        cv2.putText(img, txt, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, col, 2, cv2.LINE_AA)


def draw(img, cam, colour, thick=2):
    for P in camtrack.ground_lines_px(cam):
        ok = np.isfinite(P).all(1)
        if ok.sum() > 1:
            cv2.polylines(img, [np.round(P[ok]).astype(np.int32)], False, colour, thick,
                          cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", default="sAjkpeRq4P4")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--window", type=int, default=30, help="frames averaged for the setup fit")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    import run_refs as R
    video = next(p for p in (REPO / "data" / "incoming").rglob(f"{a.clip}.mp4"))
    pts = REPO / "data" / f"{a.clip}_pts.json"
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    W0 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    start = min(R.frame_positions(total, 8)[3], max(0, total - a.n - 1))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    frames = []
    while len(frames) < a.n:
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(cv2.resize(fr, WORK, interpolation=cv2.INTER_AREA)
                      if fr.shape[1] != WORK[0] else fr)
    cap.release()
    print(f"{a.clip}: {W0}px source, {len(frames)} frames from {start}, {fps:.2f} fps", flush=True)

    d = json.loads(pts.read_text(encoding="utf-8"))
    sc = WORK[0] / W0
    human = {n: np.array(d[n], float) * sc for n in DBL}

    t0 = time.time()
    seed = camera3d.CourtCamera.from_paintfit(
        paintfit.seed_camera({n: human[n].tolist() for n in DBL}, WORK[0] / 2, WORK[1] / 2, WORK),
        "seed: four human corners")
    res = camera3d.fit_camera_checked(camera3d.grey_mean(frames[:a.window]), seed)
    setup = res.camera
    chk = camera3d.paint_check(np.clip(camera3d.grey_mean(frames[:a.window]), 0, 255).astype(np.uint8),
                               setup)
    print(f"setup {time.time() - t0:.0f}s  check={setup.extra['paint_check']}  "
          f"hfov {setup.hfov_deg():.1f}  height {setup.position_m()[2]:.2f} m  "
          f"checked={sorted(chk.lines)}  unchecked={sorted(chk.unchecked)}", flush=True)

    tracker = camtrack.CameraTracker(setup)
    ref = None
    out_dir = Path(tempfile.mkdtemp())
    for i, fr in enumerate(frames):
        st = tracker.step(fr, i / fps)
        p = st.camera.project([(*court.LANDMARKS[n], 0.0) for n in DBL])
        if ref is None:
            ref = p
        moved = float(np.nanmax(np.linalg.norm(p - ref, axis=1)))
        vis = fr.copy()
        col = (60, 220, 60) if st.locked else (40, 40, 240)
        draw(vis, st.camera, col, 2)
        if i == 0:
            for n in DBL:
                cv2.circle(vis, tuple(int(v) for v in human[n]), 10, (0, 200, 255), 2, cv2.LINE_AA)
        verified = ", ".join(sorted(chk.lines)) or "none"
        label(vis, [
            (f"{a.clip} - REAL FOOTAGE, no metric truth: no cm error can be shown", (255, 255, 255)),
            (f"3D court: {st.status}  {'LOCKED' if st.locked else 'NOT LOCKED'}", col),
            (f"court moved {moved:5.1f} px since frame 0 (tripod: should be ~0)", (255, 255, 255)),
        ])
        label(vis, [
            (f"on-paint check VERIFIED: {verified}", (60, 220, 60)),
            (f"COULD NOT verify (too thin at 1080p): {', '.join(sorted(chk.unchecked))}",
             (0, 200, 255)),
            ("yellow = human-clicked corners (agreement only, ~5.8 px@640 click spread)",
             (0, 200, 255)),
        ], y0=WORK[1] - 110)
        cv2.imwrite(str(out_dir / f"f{i:04d}.png"), vis)
        if i % 25 == 0:
            print(f"  frame {i:3d} {st.status:9s} locked={st.locked} moved {moved:.1f} px "
                  f"({time.time() - t0:.0f}s)", flush=True)

    out = Path(a.out or REPO / "data" / "output" / f"court_real_{a.clip}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", f"{fps:.3f}",
                    "-i", str(out_dir / "f%04d.png"),
                    "-vf", "tpad=start_mode=clone:start_duration=1.5,scale=1600:-2,format=yuv420p",
                    "-c:v", "libx264", "-crf", "20", str(out)], check=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
