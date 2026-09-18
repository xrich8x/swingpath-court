"""court_track_video.py - a video of the 3D court camera tracking a swaying, knocked
fence-mount camera. SYNTHETIC: every frame is rendered by tools/court_track_sim.py
from a known camera, so the overlay's error is printed against that truth.

Left:  camtrack (keypoint PnP seed -> checked paint fit -> checked pose tracker).
       Court drawn green while the paint check passes, red while it does not.
Right: the shipped per-frame snap, calibration.court_lock_step, from the same start.

    cd backend && .venv/Scripts/python.exe ../tools/court_track_video.py --out demo.mp4
"""
from __future__ import annotations

import argparse
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

import court_track_sim as S                                       # noqa: E402
from swingvision import calibration, camera3d, camtrack, court    # noqa: E402

WH = (1920, 1080)


def draw_court(img, polylines, colour, thick=3):
    for P in polylines:
        P = np.asarray(P, float)
        ok = np.isfinite(P).all(1)
        if ok.sum() >= 2:
            cv2.polylines(img, [np.round(P[ok]).astype(np.int32)], False, colour, thick,
                          cv2.LINE_AA)


def homography_lines(Hm, n=50):
    out = []
    for a, b in court.LINES:
        t = np.linspace(0, 1, n)[:, None]
        xy = (1 - t) * np.array(a) + t * np.array(b)
        out.append(calibration.court_to_image(Hm, xy))
    return out


def label(img, lines, y0=44):
    for i, (txt, col) in enumerate(lines):
        y = y0 + i * 44
        cv2.putText(img, txt, (14, y), cv2.FONT_HERSHEY_SIMPLEX, 1.15, (0, 0, 0), 7, cv2.LINE_AA)
        cv2.putText(img, txt, (14, y), cv2.FONT_HERSHEY_SIMPLEX, 1.15, col, 3, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=200)
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--knock-scale", type=float, default=3.0)
    ap.add_argument("--out", default=str(REPO / "data" / "output" / "court_track_demo.mp4"))
    a = ap.parse_args()

    r_path, r_img, r_seed = [np.random.default_rng(s)
                             for s in np.random.SeedSequence(a.seed).spawn(3)]
    p0 = S.base_pitch(WH)
    path = S.sway_path(a.n, r_path, knock_scale=a.knock_scale)
    truths = [S.camera(p[0], p0 + p[1], p[2], p[3], p[4], p[5], wh=WH) for p in path]
    t0 = time.time()
    f0 = S.render(truths[0], r_img)
    kps = {nm: tuple(np.array(uv) + r_seed.normal(0, 14.78 * WH[1] / 1080, 2))
           for nm, uv in zip(court.KEYPOINTS_3D,
                             truths[0].project(list(court.LANDMARKS_3D.values())))
           if np.isfinite(uv).all() and 0 <= uv[0] < WH[0] and 0 <= uv[1] < WH[1]}
    seed = camera3d.solve_pnp_seed(kps, WH)
    setup = camera3d.fit_camera_checked(f0, seed.camera).camera
    print(f"setup {time.time() - t0:.0f}s, check {setup.extra['paint_check']}", flush=True)

    tracker = camtrack.CameraTracker(setup)
    Hb = setup.ground_homography()
    with tempfile.TemporaryDirectory() as td:
        for i, tc in enumerate(truths):
            img = f0 if i == 0 else S.render(tc, r_img)
            g8 = np.clip(img, 0, 255).astype(np.uint8)
            st = tracker.step(g8, i / S.FPS)
            if i:
                A, _ = calibration.court_lock_step(np.dstack([g8] * 3), Hb)
                Hb = A @ Hb
            e_ct = max(S.line_errors(tc, st.camera.ground_point).values()) * 100
            e_ls = max(S.line_errors(tc, lambda uv: calibration.image_to_court(Hb, uv))
                       .values()) * 100

            left = cv2.cvtColor(g8, cv2.COLOR_GRAY2BGR)
            right = left.copy()
            if i == 0:
                for nm, (u, v) in kps.items():
                    cv2.circle(left, (int(u), int(v)), 6, (0, 200, 255), 2, cv2.LINE_AA)
            col = (60, 220, 60) if st.locked else (40, 40, 240)
            draw_court(left, camtrack.ground_lines_px(st.camera), col)
            draw_court(right, homography_lines(Hb), (255, 160, 40))
            knocked = i >= int(S.KNOCK_S * S.FPS)
            fmt = lambda e: f"{e:.1f} cm" if e < 100 else f"{e / 100:.1f} m"  # noqa: E731
            label(left, [("3D camera tracker (new)", (255, 255, 255)),
                         (f"{st.status}  {'LOCKED' if st.locked else 'NOT LOCKED'}", col),
                         (f"worst line error {fmt(e_ct)}", (255, 255, 255))])
            label(right, [("per-frame snap (shipped)", (255, 255, 255)),
                          (f"worst line error {fmt(e_ls)}", (255, 255, 255))])
            for pane in (left, right):
                txt = (f"SYNTHETIC  t={i / S.FPS:4.2f}s  fence sway"
                       + ("  + KNOCK" if knocked else ""))
                label(pane, [(txt, (0, 220, 255) if knocked else (200, 200, 200))],
                      y0=WH[1] - 20)
            frame = np.hstack([left, np.full((WH[1], 6, 3), 255, np.uint8), right])
            cv2.imwrite(str(Path(td) / f"f{i:04d}.png"), frame)
            if i % 15 == 0:
                print(f"  frame {i} {st.status} {e_ct:.1f} cm ({time.time() - t0:.0f}s)",
                      flush=True)
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        # first frame held 1.5 s so the keypoints and the setup court can be seen
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(S.FPS),
                        "-i", str(Path(td) / "f%04d.png"),
                        "-vf", "tpad=start_mode=clone:start_duration=1.5,"
                               "scale=2560:-2,format=yuv420p",
                        "-c:v", "libx264", "-crf", "20", str(out)], check=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
