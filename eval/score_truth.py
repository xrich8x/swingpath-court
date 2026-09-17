"""eval/score_truth.py - can the agreement score TELL the true court from a wrong one?

The search-free feedback loop for any change to the mask or the scoring. Every
other harness here runs the full seed-search, which costs minutes and mixes two
questions together: "can the criteria recognise the right answer" and "can the
search find it". This asks only the first, by handing the scorer the court a
HUMAN placed.

WHY SEPARATION, NOT LEVEL. The seed-grid sweep (data/output/court_why_it_fails.md
section 6) widened the search, reached courts the old grid could not, and got
every one of them wrong - because a higher score at the true court is worthless if
wrong courts rise with it. So the headline here is the MARGIN:

    margin = g(true court) - max g(court that is >20 px from the true court)

  margin > 0  the truth outscores every wrong candidate -> a search can win
  margin < 0  a wrong court outscores the truth         -> no search can win

The distractor pool is the shipped coarse grid, which is what `autodetect`
actually ranks, so a negative margin here is a live failure and not a contrived one.

READ THIS BEFORE QUOTING ANY NUMBER FROM HERE. This harness scores the criteria at
the human's four clicked corners, EXACTLY. The gate does not define "correct" that
way - it defines correct as within 20 px at 640 wide, and the clicks are one sample
from that neighbourhood, measured NOT to be the best-registered one. So every g and
every margin printed here is a LOWER BOUND on what the criteria can do.

Measured 2026-08-24 (`eval/truth_neighbourhood.py`): at a median 5.8 px from the
clicks - still well inside the gate's own tolerance - the true court clears the 0.33
accept gate on 9 of 10 reference clips rather than 5, and the median margin rises
from +0.126 to +0.210. A claim this file's output had already put into the record,
"the criteria reject the correct answer even when handed it", was withdrawn on that
evidence.

Use `truth_neighbourhood.py` when the question is "can the criteria recognise this
court". Use this file only when the question is specifically about the clicked
corners themselves.

Ground truth is human only: per-frame clicks for the 20 court gold clips, and the
`"_exact": true` hand placements for the reference clips. `eala_pts_auto.json` is
excluded - scoring against a detector's own output is self-grading.

    backend/.venv/Scripts/python.exe eval/score_truth.py
    backend/.venv/Scripts/python.exe eval/score_truth.py --mask clay --frames 3
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))

from swingvision.courtfit import DBL  # noqa: E402

GOLD = REPO / "data" / "gold"
WRONG_PX_640 = 20.0     # the empty gap between right and wrong courts, at 640 wide


def _mask_fn(kind, calibration):
    from swingvision import courtfit as cf
    if kind == "clay":
        return lambda f: cf._clay_mask(f, calibration)
    if kind.startswith("fused"):
        import masks_candidate as mc          # eval/ only - never shipped
        kw = mc.VARIANTS[kind]
        return lambda f: mc.fused_mask(f, calibration, **kw)
    return calibration.line_ridge_mask


def truth_sources(limit_frames: int):
    """[(clip, source, [(frame_key, image, named_corners)])] - human courts only."""
    import cv2

    out = []
    for lf in sorted(GOLD.glob("*.court.labels.json")):
        clip = lf.name.replace(".court.labels.json", "")
        labs = json.loads(lf.read_text(encoding="utf-8"))["labels"]
        usable = [(k, v) for k, v in labs.items()
                  if v.get("court") is True
                  and all(n in v.get("keypoints", {}) for n in DBL)]
        if not usable:
            continue
        usable.sort(key=lambda kv: int(kv[0]))
        pick = usable[:: max(1, len(usable) // limit_frames)][:limit_frames]
        frames = []
        for k, v in pick:
            im = cv2.imread(str(GOLD / "frames" / clip / f"f{int(k):05d}.jpg"))
            if im is not None:
                frames.append((k, im, {n: v["keypoints"][n] for n in DBL}))
        if frames:
            out.append((clip, "gold", frames))

    sys.path.insert(0, str(REPO / "eval"))
    from run_refs import references, frames_from
    for clip, pts_path, vid in references():
        ref = json.loads(pts_path.read_text(encoding="utf-8"))
        named = {n: ref[n] for n in DBL if n in ref}
        if len(named) < 4:
            continue
        frames = [(str(p), im, named) for p, im in frames_from(vid, limit_frames)]
        if frames:
            out.append((clip, "ref", frames))
    return out


def margin_for_frame(img, named, calibration, court, cf, mask_fn):
    """(g_true, g_best_wrong, margin). Distractors = the SHIPPED coarse grid."""
    dt, cos2, sin2, w, h, _lines = cf._precompute(img, calibration, mask_fn)
    tol = max(2.0, w * 0.006)
    court_pts = [court.LANDMARKS[n] for n in DBL]
    scale = 640.0 / w                                  # compare px at 640 wide

    H_true = calibration.compute_homography(court_pts, [named[n] for n in DBL])
    g_true, _nl, _ev = cf._ori_detail(H_true, calibration, court,
                                      dt, cos2, sin2, w, h, tol, 0.80)
    true_xy = np.array([calibration.court_to_image(H_true, [court.LANDMARKS[n]])[0]
                        for n in DBL])

    grid = cf.COARSE_GRID
    ax = [np.asarray(v) * (w if i in (0, 3, 4) else h) for i, v in enumerate(grid)]
    best_wrong = 0.0
    for cx, yn, yf, wn, wf in itertools.product(*ax):
        c = cf._corners(cx, yn, yf, wn, wf)
        cand = np.array([c[n] for n in DBL], float)
        if float(np.mean(np.hypot(*(cand - true_xy).T))) * scale <= WRONG_PX_640:
            continue                                   # this IS the true court
        try:
            H = calibration.compute_homography(court_pts, [c[n] for n in DBL])
        except Exception:
            continue
        g, _n, _e = cf._ori_detail(H, calibration, court, dt, cos2, sin2, w, h, tol, 0.80)
        if g > best_wrong:
            best_wrong = g
    return g_true, best_wrong, g_true - best_wrong


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mask", default="white",
                    choices=("white", "clay", "fused", "fused_nochroma",
                             "fused_noclahe", "fused_raw",
                             "plain_L", "plain_L_raw"))
    ap.add_argument("--frames", type=int, default=3, help="frames per clip")
    ap.add_argument("--clips", nargs="*")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from swingvision import calibration, court
    from swingvision import courtfit as cf
    mask_fn = _mask_fn(a.mask, calibration)

    srcs = truth_sources(a.frames)
    if a.clips:
        srcs = [s for s in srcs if s[0] in set(a.clips)]

    print(f"mask={a.mask}  frames/clip={a.frames}  distractors=the shipped coarse grid\n")
    print(f"{'clip':24s} {'src':>5s} {'g@truth':>8s} {'g@wrong':>8s} {'margin':>7s}  verdict")
    print("-" * 72)
    rows = []
    for clip, src, frames in srcs:
        ms = [margin_for_frame(im, named, calibration, court, cf, mask_fn)
              for _k, im, named in frames]
        gt = float(np.median([m[0] for m in ms]))
        gw = float(np.median([m[1] for m in ms]))
        mg = gt - gw
        rows.append({"clip": clip, "src": src, "g_true": gt, "g_wrong": gw, "margin": mg})
        v = ("truth wins" if mg > 0 else "WRONG COURT OUTSCORES TRUTH")
        print(f"{clip:24s} {src:>5s} {gt:8.3f} {gw:8.3f} {mg:7.3f}  {v}")

    lose = [r for r in rows if r["margin"] <= 0]
    print("-" * 72)
    print(f"{len(rows) - len(lose)}/{len(rows)} clips where the true court outscores every "
          f"grid distractor.  median margin {np.median([r['margin'] for r in rows]):+.3f}")
    if lose:
        print(f"LOSES on: {', '.join(r['clip'] for r in lose)}")
    print(f"\nAlso: g@truth below the 0.33 accept gate on "
          f"{sum(1 for r in rows if r['g_true'] < 0.33)}/{len(rows)} clips.")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
