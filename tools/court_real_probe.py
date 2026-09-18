"""court_real_probe.py - the 3D court camera on REAL footage, where there is no metric truth.

WHAT THIS CAN AND CANNOT SAY
----------------------------
No real clip here has metric court truth (no court visit). So nothing below is an
ACCURACY number. Each quantity says what it was measured against:

  lock       - camera3d.paint_check on the fitted camera: does it put every
               checkable line on the painted lines in THIS image? (lock/no-lock)
  vs_human   - pixel disagreement (px@640) between the fitted camera's four doubles
               corners and the human-clicked corners in data/<clip>_pts.json.
               AGREEMENT with a person whose own click spread is ~5.8 px@640 and
               whose placements are partly contested (calibration-provenance.md).
  repeat     - worst-line ground disagreement (m) between the fit from the clean
               human seed and fits from NOISY seeds (sigma 14.78 px@1080): whether
               the fit returns to the same camera. Repeatability, not accuracy.
  track      - camtrack over the clip from the fitted camera: fraction of frames
               the paint check passes, and how far the tracked court moves in the
               image (px@1080) on a camera believed static (a tripod).
  courtnet   - an automatic seed: CourtNetKeypoints (courtnet_split.pt, whose
               training clips do not include any pool clip BY NAME) -> PnP ->
               checked paint fit; whether it reaches the human-seeded camera.

Frames: 30 consecutive frames starting at the eval's own sample 4 of 8
(eval/run_refs.frame_positions), averaged; 4K is downscaled to 1920x1080 (the paint
fit's measured resolution). Clips: eval/run_refs.references() (strict-16 pool).
Pre-registration: docs/evidence/court-camera3d-real.md.

    cd backend && .venv/Scripts/python.exe ../tools/court_real_probe.py --workers 8
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import zlib
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "eval"))
sys.path.insert(0, str(REPO))

import court_map_ceiling as C1                                        # noqa: E402
from swingvision import camera3d, camtrack, court, courtfit, paintfit  # noqa: E402

OUT = REPO / "data" / "output" / "court_real_probe"
WORK = (1920, 1080)
WINDOW = 30
N_NOISY = 5
SEED_SIGMA = 14.78
TRACK_MAX = 180
DBL = paintfit.CORNERS


def read_frames(video, start, n):
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    out = []
    while len(out) < n:
        ok, fr = cap.read()
        if not ok:
            break
        if fr.shape[1] != WORK[0]:
            fr = cv2.resize(fr, WORK, interpolation=cv2.INTER_AREA)
        out.append(fr)
    cap.release()
    return out


def cam_lines_disagree(a, b):
    """Worst perpendicular ground distance (m) over C1's line halves between two
    cameras: points on each line imaged by `a`, back-projected through `b`."""
    worst = 0.0
    for _name, p, q, nrm in C1.lines():
        t = np.linspace(0, 1, 11)[:, None]
        xy = (1 - t) * np.array(p) + t * np.array(q)
        uv = a.project(np.column_stack([xy, np.zeros(11)]))
        ok = np.isfinite(uv).all(1)
        if not ok.any():
            continue
        g = b.ground_point(uv[ok])
        e = np.abs((g - xy[ok]) @ np.array(nrm, float))
        worst = max(worst, float(np.nanmax(e)) if np.isfinite(e).any() else math.inf)
    return worst


def corners_px640(cam, human, W):
    pr = cam.project([(*court.LANDMARKS[n], 0.0) for n in DBL])
    d = [float(np.hypot(*(pr[i] - human[n]))) * 640.0 / W for i, n in enumerate(DBL)]
    return d


def fit(img, seed_cam):
    try:
        res = camera3d.fit_camera_checked(img, seed_cam)
        return res.camera
    except Exception as ex:          # noqa: BLE001 - a failed fit is a result
        return repr(ex)


def cam_summary(cam, img8, human):
    if isinstance(cam, str):
        return {"ok": False, "error": cam}
    chk = camera3d.paint_check(img8, cam)
    return {"ok": True, "lock": chk.ok, "worst_line": chk.worst,
            "lines": {k: v[0] for k, v in chk.lines.items()}, "support": chk.support,
            "f_px": cam.f_px, "hfov_deg": cam.hfov_deg(),
            "height_m": float(cam.position_m()[2]), "lam": cam.dist[0] if cam.dist else 0.0,
            "vs_human_px640": corners_px640(cam, human, WORK[0]),
            "starts": cam.extra.get("starts"), "camera": cam.to_dict()}


def run_clip(job):
    clip, pts, video = job["clip"], Path(job["pts"]), Path(job["video"])
    t0 = time.time()
    import run_refs as R
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    W0 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cap.release()
    start = min(R.frame_positions(total, 8)[3], max(0, total - WINDOW - 1))
    frames = read_frames(video, start, WINDOW)
    img = camera3d.grey_mean(frames)
    img8 = np.clip(img, 0, 255).astype(np.uint8)
    sc = WORK[0] / W0
    d = json.loads(pts.read_text(encoding="utf-8"))
    human = {n: np.array(d[n], float) * sc for n in DBL}
    row = {"clip": clip, "video_wh": W0, "fps": fps, "frames": total, "window_start": start}
    cv2.imwrite(str(Path(job["outdir"]) / f"{clip}_mean.jpg"), img8)

    # 1. clean human seed (a first guess, as a detector would give; rule: never a precision input)
    seed = camera3d.CourtCamera.from_paintfit(
        paintfit.seed_camera({n: human[n].tolist() for n in DBL}, WORK[0] / 2, WORK[1] / 2, WORK),
        "seed: four human corners")
    base = fit(img, seed)
    row["human_seed"] = cam_summary(base, img8, human)
    row["human_seed_only"] = cam_summary(seed, img8, human)

    # 2. repeatability from noisy seeds
    rng = np.random.default_rng([job["seed"], zlib.crc32(clip.encode())])
    reps = []
    for _ in range(N_NOISY):
        noisy = {n: (human[n] + rng.normal(0, SEED_SIGMA, 2)).tolist() for n in DBL}
        try:
            s = camera3d.CourtCamera.from_paintfit(
                paintfit.seed_camera(noisy, WORK[0] / 2, WORK[1] / 2, WORK), "noisy seed")
        except Exception as ex:      # noqa: BLE001
            reps.append({"ok": False, "error": repr(ex)})
            continue
        c = fit(img, s)
        r = cam_summary(c, img8, human)
        if r["ok"] and not isinstance(base, str):
            r["vs_clean_m"] = cam_lines_disagree(base, c)
        r.pop("camera", None)
        reps.append(r)
    row["noisy_seeds"] = reps

    # 3. automatic seed: CourtNet keypoints -> PnP -> checked fit
    try:
        kps = courtfit.CourtNetKeypoints().detect(frames[len(frames) // 2])
        row["courtnet_n_kps"] = 0 if kps is None else len(kps.px)
        s = camera3d.solve_pnp_seed(kps, WORK) if kps is not None else None
        if s is None:
            row["courtnet"] = {"ok": False, "error": "no PnP seed"}
        else:
            c = fit(img, s.camera)
            r = cam_summary(c, img8, human)
            if r["ok"] and not isinstance(base, str):
                r["vs_clean_m"] = cam_lines_disagree(base, c)
            r.pop("camera", None)
            row["courtnet"] = r
    except Exception as ex:          # noqa: BLE001
        row["courtnet"] = {"ok": False, "error": repr(ex)}

    # 4. tracking from the human-seeded camera over the clip from the window start
    if not isinstance(base, str):
        n_tr = min(TRACK_MAX, total - start)
        tr = camtrack.CameraTracker(base)
        ref = None
        locked, moves, status = [], [], []
        cap = cv2.VideoCapture(str(video))
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        world = np.array([(*court.LANDMARKS[n], 0.0) for n in DBL]
                         + [(court.X_CENTER, court.Y_FAR_BASELINE, 0.0),
                            (court.X_CENTER, court.Y_NEAR_BASELINE, 0.0)])
        for i in range(n_tr):
            ok, fr = cap.read()
            if not ok:
                break
            if fr.shape[1] != WORK[0]:
                fr = cv2.resize(fr, WORK, interpolation=cv2.INTER_AREA)
            st = tr.step(fr, i / fps)
            p = st.camera.project(world)
            if ref is None:
                ref = p
            moves.append(float(np.nanmax(np.linalg.norm(p - ref, axis=1))))
            locked.append(bool(st.locked))
            status.append(st.status)
        cap.release()
        row["track"] = {"frames": len(locked), "lock_frac": float(np.mean(locked)) if locked else 0,
                        "status": {s: status.count(s) for s in set(status)},
                        "move_px_p50": float(np.median(moves)) if moves else None,
                        "move_px_max": float(np.max(moves)) if moves else None,
                        "move_px_series": moves, "locked_series": locked}

    # contact image for a human eye (rule 9)
    vis = cv2.cvtColor(img8, cv2.COLOR_GRAY2BGR)
    if not isinstance(base, str):
        col = (60, 220, 60) if row["human_seed"]["lock"] else (40, 40, 240)
        for P in camtrack.ground_lines_px(base):
            ok = np.isfinite(P).all(1)
            if ok.sum() > 1:
                cv2.polylines(vis, [np.round(P[ok]).astype(np.int32)], False, col, 2, cv2.LINE_AA)
    for n in DBL:
        cv2.circle(vis, tuple(int(v) for v in human[n]), 9, (0, 220, 255), 2, cv2.LINE_AA)
    cv2.putText(vis, f"{clip}  green/red = fitted 3D court (paint check)  yellow = human corners",
                (14, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 6, cv2.LINE_AA)
    cv2.putText(vis, f"{clip}  green/red = fitted 3D court (paint check)  yellow = human corners",
                (14, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(Path(job["outdir"]) / f"{clip}_fit.jpg"), vis)
    row["t_s"] = round(time.time() - t0, 1)
    print(f"  {clip}: {row['t_s']}s", flush=True)
    return row


def _json(o):
    if isinstance(o, dict):
        return {str(k): _json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json(v) for v in o]
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return v if math.isfinite(v) else str(v)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def main():
    from concurrent.futures import ProcessPoolExecutor
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clips", nargs="*", help="default: the strict-16 references pool")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 4))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    import run_refs as R
    refs = R.references()
    if a.clips:
        cand = {p.stem[:-4]: p for p in (REPO / "data").glob("*_pts.json")}
        vids = {v.stem: v for v in (REPO / "data" / "incoming").rglob("*.mp4")
                if "Raw" not in str(v)}
        refs = [(c, cand[c], vids[c]) for c in a.clips]
    outdir = Path(a.out or OUT / f"seed{a.seed}")
    outdir.mkdir(parents=True, exist_ok=True)
    jobs = [{"clip": c, "pts": str(p), "video": str(v), "seed": a.seed, "outdir": str(outdir)}
            for c, p, v in refs]
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(run_clip, jobs, chunksize=1))
    res = {"stamp": {"tool": "tools/court_real_probe.py", "seed": a.seed,
                     "clips": [j["clip"] for j in jobs], "work_wh": WORK, "window": WINDOW,
                     "noisy_seeds": N_NOISY, "seed_sigma_px_1080": SEED_SIGMA,
                     "courtnet_weights": courtfit.COURTNET_SPLIT_WEIGHTS,
                     "wall_s": round(time.time() - t0, 1)},
           "rows": rows}
    (outdir / "probe.json").write_text(json.dumps(_json(res), indent=1), encoding="utf-8")
    print_table(rows)
    print("wrote", outdir / "probe.json")


def print_table(rows):
    print(f"{'clip':18s} {'lock':5s} {'worst':15s} {'hfov':>5s} {'h m':>5s} "
          f"{'vsHum p640':>11s} {'rep ok':>6s} {'rep m max':>9s} {'CN kp':>5s} {'CN':>10s} "
          f"{'trk lock':>8s} {'move px':>8s}")
    for r in rows:
        h = r["human_seed"]
        if not h["ok"]:
            print(f"{r['clip']:18s} FIT FAILED {h['error'][:60]}")
            continue
        reps = [x for x in r["noisy_seeds"] if x.get("ok")]
        rep_ok = sum(1 for x in reps if x.get("vs_clean_m", 9) <= 0.05)
        rep_max = max((x.get("vs_clean_m", math.inf) for x in reps), default=math.inf)
        cn = r.get("courtnet", {})
        cn_s = ("-" if not cn.get("ok") else
                f"{'L' if cn['lock'] else 'x'} {cn.get('vs_clean_m', math.inf):.2f}m")
        tk = r.get("track", {})
        print(f"{r['clip']:18s} {str(h['lock']):5s} {str(h['worst_line']):15s} "
              f"{h['hfov_deg']:5.1f} {h['height_m']:5.2f} {np.median(h['vs_human_px640']):11.1f} "
              f"{rep_ok:>3d}/{len(r['noisy_seeds'])} {rep_max:9.3f} {r.get('courtnet_n_kps', 0):5d} "
              f"{cn_s:>10s} {tk.get('lock_frac', 0):8.2f} {tk.get('move_px_max') or 0:8.1f}")


if __name__ == "__main__":
    main()
