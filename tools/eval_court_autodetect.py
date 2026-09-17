"""Single-frame eval of the court auto-detector on the gold labels.

The DETECTOR lives in backend/swingvision/courtfit.py (line-fit + camera-angle
prior + regulation-structure matching + physical camera gate — see its module
docstring); this file is only the measurement harness, kept in tools/ with the
other eval scripts. Clip-level consensus scoring (the product metric) is
tools/eval_court_consensus.py.

Scored against the human gold labels (same metrics as eval_court):
  detect%   fraction of usable frames an auto court was returned + verified
  corner    median px error of the 4 baseline corners vs the human clicks
  kp_err    median px error over all 14 keypoints
  IoU       court-outline overlap with the human court
  false%    unusable frames that wrongly returned a court (must stay ~0)

  backend/.venv/Scripts/python.exe tools/eval_court_autodetect.py --all --per-clip 3
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

from swingvision import courtfit as _courtfit
from swingvision.courtfit import DBL, autodetect  # noqa: F401  (engine in the package)


def __getattr__(name):  # keep `ad._anything` working for older scripts
    return getattr(_courtfit, name)


def _quad_iou(a, b):
    """Convex-quad IoU via shoelace + Sutherland-Hodgman (eval metric only;
    orientation-normalised clipper, unlike eval_court.quad_iou — kept verbatim
    so historical IoU numbers stay comparable)."""
    def area(p):
        s = 0.0
        for i in range(len(p)):
            x1, y1 = p[i]; x2, y2 = p[(i + 1) % len(p)]
            s += x1 * y2 - x2 * y1
        return abs(s) / 2.0

    def clip(sub, clp):
        def inside(p, aa, bb):
            return (bb[0]-aa[0])*(p[1]-aa[1]) - (bb[1]-aa[1])*(p[0]-aa[0]) >= 0

        def isect(p1, p2, aa, bb):
            x1, y1 = p1; x2, y2 = p2; x3, y3 = aa; x4, y4 = bb
            den = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
            if abs(den) < 1e-9:
                return p2
            t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / den
            return (x1 + t*(x2-x1), y1 + t*(y2-y1))
        s = 0.0
        for i in range(len(clp)):
            x1, y1 = clp[i]; x2, y2 = clp[(i+1) % len(clp)]
            s += x1*y2 - x2*y1
        if s < 0:
            clp = clp[::-1]
        out = sub
        for i in range(len(clp)):
            aa, bb = clp[i], clp[(i+1) % len(clp)]
            inp, out = out, []
            for j in range(len(inp)):
                cur, prv = inp[j], inp[j-1]
                if inside(cur, aa, bb):
                    if not inside(prv, aa, bb):
                        out.append(isect(prv, cur, aa, bb))
                    out.append(cur)
                elif inside(prv, aa, bb):
                    out.append(isect(prv, cur, aa, bb))
            if not out:
                return []
        return out
    inter = clip(a, b)
    if len(inter) < 3:
        return 0.0
    ai = area(inter)
    return ai / (area(a) + area(b) - ai + 1e-9)


def score_clip(clip, per_clip, topk, use_prior=True):
    lab_path = GOLD / f"{clip}.court.labels.json"
    if not lab_path.exists():
        return None
    import cv2
    from swingvision import calibration, court

    labs = json.loads(lab_path.read_text(encoding="utf-8"))["labels"]
    frames_dir = GOLD / "frames" / clip
    usable = [k for k, v in labs.items()
              if v.get("court") is True and all(n in v.get("keypoints", {}) for n in DBL)]
    unusable = [k for k, v in labs.items() if v.get("court") is False]
    if per_clip:
        usable = usable[:: max(1, len(usable) // per_clip)][:per_clip]
        unusable = unusable[:per_clip]

    det = 0
    corner_e, kp_e, ious = [], [], []
    for k in usable:
        img = cv2.imread(str(frames_dir / f"f{int(k):05d}.jpg"))
        if img is None:
            continue
        res = autodetect(img, calibration, court, topk=topk, use_prior=use_prior)
        if res is None:
            continue
        det += 1
        H = res[0]
        gk = labs[k]["keypoints"]
        corner_e += [float(np.hypot(*(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                                      - np.array(gk[n])))) for n in DBL]
        kp_e += [float(np.hypot(*(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                                  - np.array(gk[n])))) for n in gk if n in court.LANDMARKS]
        pc = [tuple(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]) for n in DBL]
        ious.append(_quad_iou(pc, [tuple(gk[n]) for n in DBL]))

    false = 0
    for k in unusable:
        img = cv2.imread(str(frames_dir / f"f{int(k):05d}.jpg"))
        if img is None:
            continue
        if autodetect(img, calibration, court, topk=topk) is not None:
            false += 1

    return {"clip": clip, "usable": len(usable), "det": det,
            "detect_pct": 100 * det / len(usable) if usable else 0.0,
            "corner": median(corner_e) if corner_e else None,
            "kp": median(kp_e) if kp_e else None,
            "iou": median(ious) if ious else None,
            "unusable": len(unusable),
            "false_pct": 100 * false / len(unusable) if unusable else None}


def fmt(x, s="{:.1f}"):
    return "  -  " if x is None else s.format(x)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clips", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--per-clip", type=int, default=3, help="frames per clip (0=all)")
    ap.add_argument("--topk", type=int, default=8, help="candidates to snap+verify")
    ap.add_argument("--no-prior", action="store_true", help="disable the camera-angle prior")
    args = ap.parse_args()

    clips = args.clips
    if args.all or not clips:
        clips = sorted(p.name[:-len(".court.labels.json")]
                       for p in GOLD.glob("*.court.labels.json"))
    print(f"camera-angle prior: {'OFF' if args.no_prior else 'ON'}")

    hdr = (f"{'clip':22s} {'frm':>3s} {'detect%':>7s} {'corner':>6s} "
           f"{'kp_err':>6s} {'IoU':>5s} {'false%':>6s}")
    print(hdr); print("-" * len(hdr))
    agg = {"det": [], "cor": [], "iou": [], "false": []}
    for c in clips:
        r = score_clip(c, args.per_clip if args.per_clip else 0, args.topk,
                       use_prior=not args.no_prior)
        if r is None:
            continue
        print(f"{r['clip']:22s} {r['usable']:3d} {fmt(r['detect_pct']):>7s} "
              f"{fmt(r['corner']):>6s} {fmt(r['kp']):>6s} "
              f"{fmt(r['iou'],'{:.2f}'):>5s} {fmt(r['false_pct']):>6s}")
        agg["det"].append(r["detect_pct"])
        if r["corner"] is not None:
            agg["cor"].append(r["corner"])
        if r["iou"] is not None:
            agg["iou"].append(r["iou"])
        if r["false_pct"] is not None:
            agg["false"].append(r["false_pct"])
    print("-" * len(hdr))
    print(f"{'MEAN':22s} {'':3s} {fmt(np.mean(agg['det'])):>7s} "
          f"{fmt(np.median(agg['cor']) if agg['cor'] else None):>6s} "
          f"{'':6s} {fmt(np.median(agg['iou']) if agg['iou'] else None,'{:.2f}'):>5s} "
          f"{fmt(np.mean(agg['false']) if agg['false'] else None):>6s}")


if __name__ == "__main__":
    main()
