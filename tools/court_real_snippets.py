"""court_real_snippets.py - short overlay videos of the 3D court camera on REAL clips.

For a human eye, not a score. Real footage here has NO measured court, so these
snippets show whether the court LOCKS onto the paint and whether it STAYS put -
never how accurate it is (docs/evidence/court-camera3d.md; CLAUDE.md hard rule 1).

Per clip, exactly as tools/court_real_probe.py does it:
  1. a 30-frame window at the eval's own sample 4 of 8 (eval/run_refs.frame_positions),
     averaged; 4K is downscaled to 1920x1080;
  2. the four human-clicked corners in data/<clip>_pts.json make a ROUGH seed (a
     first guess, as a detector would give; never a precision input);
  3. camera3d.fit_camera_checked decides the camera;
  4. camtrack.CameraTracker follows it from that window for --seconds.

Drawn on every frame: the court from the tracked camera, GREEN while the paint
check passes over the whole court, AMBER while it passes on the near half only
(the far lines unverified), RED while it fails; the tracker's status and claim.

    cd backend
    .venv\\Scripts\\python.exe ..\\tools\\court_real_snippets.py
    .venv\\Scripts\\python.exe ..\\tools\\court_real_snippets.py --clips sAjkpeRq4P4 --seconds 20

Default clips (2 hard, 2 shell, 1 clay; every one has human corners):
  UHf0LeMU2pg, uR5q2cSM6AY (Hardcourt) - hillsborough_p02, flexi_joy_p01 (Shell,
  static tripods) - sAjkpeRq4P4 (Clay, the best clip in the capture census).
Writes data/output/court_real_snippets/<clip>.mp4 and a summary JSON.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "eval"))
sys.path.insert(0, str(REPO))

from swingvision import camera3d, camtrack, paintfit             # noqa: E402

OUT = REPO / "data" / "output" / "court_real_snippets"
WORK = (1920, 1080)
WINDOW = 30
DBL = paintfit.CORNERS
DEFAULT = {"UHf0LeMU2pg": "Hardcourt", "uR5q2cSM6AY": "Hardcourt",
           "hillsborough_p02": "Shell", "flexi_joy_p01": "Shell", "sAjkpeRq4P4": "Clay"}
GREEN, AMBER, RED = (60, 220, 60), (0, 190, 255), (40, 40, 240)


def find_video(clip):
    hits = [v for v in (REPO / "data" / "incoming").rglob("*")
            if v.suffix.lower() in (".mp4", ".mov", ".mkv") and v.stem == clip
            and "Raw - Do Not Process" not in str(v)]
    return hits[0] if hits else None


def read(cap):
    ok, fr = cap.read()
    if not ok:
        return None
    return cv2.resize(fr, WORK, interpolation=cv2.INTER_AREA) if fr.shape[1] != WORK[0] else fr


def text(img, lines, y0=40, scale=1.0):
    for i, (s, col) in enumerate(lines):
        y = y0 + i * int(40 * scale)
        cv2.putText(img, s, (14, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 6, cv2.LINE_AA)
        cv2.putText(img, s, (14, y), cv2.FONT_HERSHEY_SIMPLEX, scale, col, 2, cv2.LINE_AA)


def draw(img, cam, col):
    for P in camtrack.ground_lines_px(cam):
        P = np.asarray(P, float)
        ok = np.isfinite(P).all(1)
        if ok.sum() >= 2:
            cv2.polylines(img, [np.round(P[ok]).astype(np.int32)], False, col, 3, cv2.LINE_AA)


class Writer:
    """H.264 through the bundled ffmpeg (imageio-ffmpeg, already a requirement),
    so the file plays anywhere; mp4v through OpenCV if that is missing."""

    def __init__(self, path, fps, wh):
        self.p = None
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            self.p = subprocess.Popen(
                [exe, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                 "-s", f"{wh[0]}x{wh[1]}", "-r", f"{fps:.3f}", "-i", "-",
                 "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", str(path)],
                stdin=subprocess.PIPE)
        except Exception:
            self.cv = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, wh)

    def write(self, img):
        if self.p:
            self.p.stdin.write(np.ascontiguousarray(img).tobytes())
        else:
            self.cv.write(img)

    def close(self):
        if self.p:
            self.p.stdin.close()
            self.p.wait()
        else:
            self.cv.release()


def run_clip(clip, surface, seconds, out_wh):
    import run_refs as R
    video = find_video(clip)
    pts = REPO / "data" / f"{clip}_pts.json"
    if video is None or not pts.exists():
        return {"clip": clip, "error": f"video {'missing' if video is None else 'ok'}, "
                                       f"corners {'ok' if pts.exists() else 'missing'}"}
    t0 = time.time()
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    W0 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    start = min(R.frame_positions(total, 8)[3], max(0, total - WINDOW - 1))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    frames = [f for f in (read(cap) for _ in range(WINDOW)) if f is not None]
    img = camera3d.grey_mean(frames)
    d = json.loads(pts.read_text(encoding="utf-8"))
    sc = WORK[0] / W0
    human = {n: np.array(d[n], float) * sc for n in DBL}
    seed = camera3d.CourtCamera.from_paintfit(
        paintfit.seed_camera({n: human[n].tolist() for n in DBL}, WORK[0] / 2, WORK[1] / 2, WORK),
        "seed: four human corners")
    res = camera3d.fit_camera_checked(img, seed)
    cam = res.camera
    setup = {"check": cam.extra.get("paint_check"), "scope": cam.extra.get("lock_scope"),
             "height_m": round(float(cam.position_m()[2]), 2),
             "hfov_deg": round(cam.hfov_deg(), 1), "starts": cam.extra.get("starts")}
    print(f"{clip} ({surface}): setup {setup} in {time.time() - t0:.0f}s", flush=True)

    tr = camtrack.CameraTracker(cam)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    n = int(round(seconds * fps))
    OUT.mkdir(parents=True, exist_ok=True)
    wr = Writer(OUT / f"{clip}.mp4", fps, out_wh)
    locked, scopes, status = [], [], []
    for i in range(n):
        fr = read(cap)
        if fr is None:
            break
        st = tr.step(fr, i / fps)
        locked.append(bool(st.locked))
        scopes.append(st.lock_scope)
        status.append(st.status)
        col = (RED if not st.locked else GREEN if st.lock_scope == "whole_court" else AMBER)
        vis = fr.copy()
        draw(vis, st.camera, col)
        verdict = ("NOT LOCKED" if not st.locked else
                   "LOCKED - whole court" if st.lock_scope == "whole_court" else
                   "LOCKED - near half only (far lines not verified)")
        text(vis, [(f"{clip}  |  {surface}  |  REAL FOOTAGE", (255, 255, 255)),
                   (f"{st.status}: {verdict}", col),
                   (f"camera {setup['height_m']} m high, {setup['hfov_deg']} deg wide  "
                    f"|  t={i / fps:5.2f}s", (230, 230, 230))])
        text(vis, [("No measured court: shows lock and stability, NOT accuracy",
                    (200, 200, 200))], y0=WORK[1] - 24, scale=0.9)
        wr.write(cv2.resize(vis, out_wh, interpolation=cv2.INTER_AREA))
    wr.close()
    cap.release()
    row = {"clip": clip, "surface": surface, "video": str(video.relative_to(REPO)),
           "fps": fps, "window_start": start, "setup": setup, "frames": len(locked),
           "locked_frac": float(np.mean(locked)) if locked else 0.0,
           "whole_court_frac": float(np.mean([s == "whole_court" for s in scopes])) if scopes else 0.0,
           "status": {s: status.count(s) for s in sorted(set(status))},
           "wall_s": round(time.time() - t0, 1), "mp4": str((OUT / f"{clip}.mp4").relative_to(REPO))}
    print(f"   {len(locked)} frames, locked {row['locked_frac']:.0%}, status {row['status']}", flush=True)
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clips", nargs="*", default=list(DEFAULT))
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--width", type=int, default=1280)
    a = ap.parse_args()
    out_wh = (a.width, int(round(a.width * WORK[1] / WORK[0] / 2) * 2))
    rows = []
    for c in a.clips:
        try:
            rows.append(run_clip(c, DEFAULT.get(c, "?"), a.seconds, out_wh))
        except Exception as ex:          # one bad clip must not stop the rest
            rows.append({"clip": c, "error": repr(ex)})
            print(f"{c}: FAILED {ex!r}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(
        {"tool": "tools/court_real_snippets.py", "what_it_shows": "lock and stability on real "
         "footage with no measured court; never accuracy", "far_lines_default":
         camera3d.FAR_LINES_DEFAULT, "rows": rows}, indent=1, default=str), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
