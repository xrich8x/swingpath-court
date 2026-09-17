"""CLEAN PLATE court detection: delete the players, then fit the empty court.

We were solving court detection as a single-PHOTO problem, but a clip is video of a
court that doesn't move. Take the per-pixel median across frames and every moving
thing (players, ball, shadows that pass) vanishes — what's left is an empty court
with unoccluded lines. Fitting THAT removes the single biggest source of weak line
support: a player standing on the very baseline we need to see.

Works for live too: at setup the court is empty, so a few seconds of video gives an
even cleaner plate.

This scores it the way the product actually works — ONE court per clip (you
calibrate once), against the human corners of every labelled frame in that clip:

  lock     did the clip get a verified court at all
  err      median px error of the 4 corners vs your clicks, across labelled frames

  backend/.venv/Scripts/python.exe tools/eval_court_cleanplate.py --all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

GOLD = REPO / "data" / "gold"
DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]


def clean_plate(frames):
    """Per-pixel median across frames -> the empty court (movers vanish)."""
    return np.median(np.stack(frames, axis=0), axis=0).astype(np.uint8)


def plate_from_video(video, cv2, n=150, span_s=90.0, start_frac=0.30):
    """The RIGHT way to build a clean plate: many frames from ONE SHORT WINDOW, so
    the light and the camera are identical and only the players move. (Medianing
    frames scattered across a whole match instead blends changing light/exposure and
    any drift, which FADES the lines — measured: it made detection worse.)"""
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return None
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if total <= 0:
        cap.release()
        return None
    start = int(total * start_frac)
    span = min(int(span_s * fps), max(1, total - start - 1))
    frames = []
    for i in np.linspace(start, start + span, n).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, im = cap.read()
        if ok:
            frames.append(im)
    cap.release()
    return clean_plate(frames) if len(frames) >= 20 else None


def load_frames(clip, cv2):
    out = []
    for p in sorted((GOLD / "frames" / clip).glob("*.jpg")):
        im = cv2.imread(str(p))
        if im is not None:
            out.append(im)
    return out


def score_clip(clip, save_dir=None):
    import cv2
    from swingvision import calibration, court
    import court_setup_server as cs

    lab_path = GOLD / f"{clip}.court.labels.json"
    if not lab_path.exists():
        return None
    labs = json.loads(lab_path.read_text())["labels"]
    usable = {k: v for k, v in labs.items()
              if v.get("court") is True and all(n in v.get("keypoints", {}) for n in DBL)}
    # Prefer a proper plate from the source video (one short window); fall back to
    # medianing the sampled gold frames (spread across the match = a poor plate).
    plate = None
    man = json.loads((GOLD / f"{clip}.court.manifest.json").read_text())
    vid = REPO / str(man.get("video", ""))
    if not str(man.get("video", "")).startswith("http") and vid.exists():
        plate = plate_from_video(vid, cv2)
    if plate is None:
        frames = load_frames(clip, cv2)
        if not frames or not usable:
            return None
        plate = clean_plate(frames)
    if not usable:
        return None

    fit = cs.auto_fit(plate)
    if fit is None:
        if save_dir:
            cv2.imwrite(str(save_dir / f"{clip}_nolock.jpg"), plate)
        return {"clip": clip, "lock": False, "err": None, "n": len(usable)}

    H = calibration.compute_homography([court.LANDMARKS[n] for n in DBL],
                                       [fit[n] for n in DBL])
    errs = []
    for v in usable.values():
        gk = v["keypoints"]
        errs.append(float(np.mean([
            np.hypot(*(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                       - np.asarray(gk[n]))) for n in DBL])))
    if save_dir:
        vis = plate.copy()
        for a, b in court.LINES:
            pa = calibration.court_to_image(H, [a])[0]
            pb = calibration.court_to_image(H, [b])[0]
            cv2.line(vis, (int(pa[0]), int(pa[1])), (int(pb[0]), int(pb[1])),
                     (90, 235, 120), 2, cv2.LINE_AA)
        cv2.imwrite(str(save_dir / f"{clip}_lock.jpg"), vis)
    return {"clip": clip, "lock": True, "err": float(np.median(errs)), "n": len(usable)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clips", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--save", default=None, help="dir to write clean-plate renders")
    args = ap.parse_args()

    clips = args.clips
    if args.all or not clips:
        clips = sorted(p.name[:-len(".court.labels.json")]
                       for p in GOLD.glob("*.court.labels.json"))
    save_dir = Path(args.save) if args.save else None
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    print(f"{'clip':22s} {'lock':>5s} {'err_px':>7s}")
    print("-" * 36)
    for c in clips:
        r = score_clip(c, save_dir)
        if r is None:
            continue
        rows.append(r)
        print(f"{r['clip']:22s} {'yes' if r['lock'] else 'no':>5s} "
              f"{('%.1f' % r['err']) if r['err'] is not None else '  -  ':>7s}")
    if save_dir:
        (save_dir / "results.json").write_text(json.dumps(rows, indent=1))
    lock = [r for r in rows if r["lock"]]
    good = [r for r in lock if r["err"] < 35]
    print("-" * 36)
    print(f"locked {len(lock)}/{len(rows)} clips | usable (<35px) {len(good)}/{len(rows)} | "
          f"median err {np.median([r['err'] for r in lock]):.1f}px" if lock else "no locks")


if __name__ == "__main__":
    main()
