"""Measure whether the geometric "court snap" refiner fixes rough manual clicks.

The claim: a user roughly marks the 4 court corners, and refine_homography_bounded
slides them until the projected court lines sit on the real white-line pixels. This
tests that claim HONESTLY on the human court gold labels, with NO new labeling.

For each gold-labeled frame we take the TRUE corners, jitter them by +/-noise px to
imitate imprecise clicks, then snap and measure how close we got back to truth:

  rough        error of the jittered corners (no snap) - the starting point
  snap_old     snap using white_line_mask (tophat+Otsu, the current default)
  snap_ridge   snap using line_ridge_mask (the amateur-robust detector)

Reported per clip (median px over frames x trials):
  corner_err   mean error of the 4 baseline corners vs the human clicks
  kp_err       mean error of ALL 14 court keypoints (projected through the snapped
               homography) vs the human clicks - the real "is the whole court right"
  cover        fraction of projected court lines landing on a real white-line pixel

A snap "works" if corner_err/kp_err drop below `rough` and cover rises. Usage:

  backend/.venv/Scripts/python.exe tools/eval_court_snap.py --all --noise 12
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

GOLD = REPO / "data" / "gold"
CORNER_NAMES = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]


def dist(p, q) -> float:
    return float(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5)


def score_clip(clip: str, noise: float, trials: int) -> dict | None:
    lab_path = GOLD / f"{clip}.court.labels.json"
    if not lab_path.exists():
        print(f"  {clip}: no labels, skip")
        return None

    import cv2
    from swingvision import calibration, court

    labels = json.loads(lab_path.read_text(encoding="utf-8"))["labels"]
    frames_dir = GOLD / "frames" / clip
    usable = {k: v for k, v in labels.items()
              if v.get("court") is True and all(n in v.get("keypoints", {}) for n in CORNER_NAMES)}

    acc = {cond: {"corner": [], "kp": [], "cover": []}
           for cond in ("rough", "snap_old", "snap_ridge")}

    def cover(H, frame):
        cov, _ = calibration.court_line_coverage(frame, H)
        return cov

    def kp_err(H, gk):
        errs = []
        for name, gxy in gk.items():
            if name in court.LANDMARKS:
                proj = calibration.court_to_image(H, [court.LANDMARKS[name]])[0]
                errs.append(dist(proj, gxy))
        return float(np.mean(errs)) if errs else None

    for key, lab in usable.items():
        img = cv2.imread(str(frames_dir / f"f{int(key):05d}.jpg"))
        if img is None:
            continue
        gk = lab["keypoints"]
        gold_corners = {n: gk[n] for n in CORNER_NAMES}
        court_pts = [court.LANDMARKS[n] for n in CORNER_NAMES]

        for t in range(trials):
            rng = np.random.default_rng(hash((clip, key, t)) & 0xFFFFFFFF)
            rough = {n: [gold_corners[n][0] + float(rng.uniform(-noise, noise)),
                         gold_corners[n][1] + float(rng.uniform(-noise, noise))]
                     for n in CORNER_NAMES}
            try:
                H_rough = calibration.compute_homography(court_pts, [rough[n] for n in CORNER_NAMES])
            except Exception:
                continue

            acc["rough"]["corner"].append(np.mean([dist(rough[n], gold_corners[n]) for n in CORNER_NAMES]))
            acc["rough"]["kp"].append(kp_err(H_rough, gk))
            acc["rough"]["cover"].append(cover(H_rough, img))

            for cond, mask_fn in (("snap_old", None), ("snap_ridge", calibration.line_ridge_mask)):
                try:
                    H, ref, _ = calibration.refine_homography_bounded(
                        img, rough, max_move_px=noise + 8.0, mask_fn=mask_fn)
                except Exception:
                    continue
                acc[cond]["corner"].append(np.mean([dist(ref[n], gold_corners[n]) for n in CORNER_NAMES]))
                acc[cond]["kp"].append(kp_err(H, gk))
                acc[cond]["cover"].append(cover(H, img))

    def med(xs):
        xs = [x for x in xs if x is not None]
        return median(xs) if xs else None

    return {"clip": clip, "frames": len(usable),
            **{cond: {m: med(acc[cond][m]) for m in ("corner", "kp", "cover")}
               for cond in acc}}


def fmt(x, s="{:5.1f}"):
    return "  -  " if x is None else s.format(x)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clips", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--noise", type=float, default=12.0, help="jitter +/-px on each corner")
    ap.add_argument("--trials", type=int, default=3, help="random jitters per frame")
    args = ap.parse_args()

    clips = args.clips
    if args.all or not clips:
        clips = sorted(p.name[:-len(".court.labels.json")]
                       for p in GOLD.glob("*.court.labels.json"))

    rows = [r for c in clips if (r := score_clip(c, args.noise, args.trials))]
    if not rows:
        raise SystemExit("no scorable clips")

    print(f"\njitter=+/-{args.noise:.0f}px, {args.trials} trials/frame | "
          f"corner_err & kp_err lower=better, cover higher=better\n")
    hdr = (f"{'clip':22s} {'frm':>3s} | "
           f"{'rough_cnr':>9s} {'old_cnr':>8s} {'ridge_cnr':>9s} | "
           f"{'rough_kp':>8s} {'old_kp':>8s} {'ridge_kp':>8s} | "
           f"{'r_cov':>5s} {'ridge_cov':>9s}")
    print(hdr)
    print("-" * len(hdr))
    agg = {c: {m: [] for m in ("corner", "kp", "cover")} for c in ("rough", "snap_old", "snap_ridge")}
    for r in rows:
        print(f"{r['clip']:22s} {r['frames']:3d} | "
              f"{fmt(r['rough']['corner']):>9s} {fmt(r['snap_old']['corner']):>8s} "
              f"{fmt(r['snap_ridge']['corner']):>9s} | "
              f"{fmt(r['rough']['kp']):>8s} {fmt(r['snap_old']['kp']):>8s} "
              f"{fmt(r['snap_ridge']['kp']):>8s} | "
              f"{fmt(r['rough']['cover'],'{:.2f}'):>5s} {fmt(r['snap_ridge']['cover'],'{:.2f}'):>9s}")
        for cond in agg:
            for m in ("corner", "kp", "cover"):
                if r[cond][m] is not None:
                    agg[cond][m].append(r[cond][m])
    print("-" * len(hdr))
    print(f"{'MEDIAN OF CLIPS':22s} {'':3s} | "
          f"{fmt(median(agg['rough']['corner'])):>9s} {fmt(median(agg['snap_old']['corner'])):>8s} "
          f"{fmt(median(agg['snap_ridge']['corner'])):>9s} | "
          f"{fmt(median(agg['rough']['kp'])):>8s} {fmt(median(agg['snap_old']['kp'])):>8s} "
          f"{fmt(median(agg['snap_ridge']['kp'])):>8s} | "
          f"{fmt(median(agg['rough']['cover']),'{:.2f}'):>5s} "
          f"{fmt(median(agg['snap_ridge']['cover']),'{:.2f}'):>9s}")


if __name__ == "__main__":
    main()
