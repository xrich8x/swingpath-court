"""eval/correspondence.py - solve WHICH LINE IS WHICH and the homography together.

Step 2 of the pre-registered build in docs/evidence/court-correspondence-gate.md.
Step 1 (eval/pencils.py) established that grouping the detected lines by CONCURRENCY
separates the court's two world-parallel families on 7 of 8 held-out shell clips.
This is the part that makes it JOINT.

THE IDEA
--------
Every failed branch settled the assignment first and then optimised. Here the
assignment is a HYPOTHESIS scored by the shipped criteria, so assignment and
homography are chosen together:

  1. take two lines from the lengthwise pencil and two from the across pencil;
  2. LABEL them with model positions - lengthwise x in {0, 1.37, 5.485, 9.60,
     10.97}, across y in {0, 5.485, 11.885, 18.285, 23.77};
  3. the four intersections now have known world coordinates, so the homography is
     exact from 4 point correspondences - no fitting, no optimiser to get trapped;
  4. score it with `_ori_detail` and `_structure`, unchanged. The best-scoring
     labelling IS the correspondence.

WHY TWO LINES PER FAMILY AND NOT FOUR
--------------------------------------
A cross-ratio needs four collinear points, so a strict cross-ratio screen requires
four lines per family. Measured in step 1, capture is a median of 2.5 of 3.5
lengthwise and 3.0 of 4.0 across - so requiring four would refuse most clips before
it started. Two lines per family plus the model's known spacings is enough to pin
the homography, and the LABEL enumeration is what recovers "which lines are these":
if the two detected lengthwise lines are really the singles sidelines, the
labelling (1.37, 9.60) says so.

Cross-ratio is therefore a SCREEN applied when a family does have four or more
lines, not a precondition. That is the role the gate reserved for it.

THE SUB-BAR, PRE-REGISTERED BEFORE THE FIRST RUN
-------------------------------------------------
    The best-scoring candidate must land within 20 px@640 of the human court on a
    MAJORITY of the tuning-pool clips (gold + 1920 references).

This is NOT C2. C2 is about end-to-end accepts through consensus; this asks the
prior question - can the solver construct the right court at all? If it cannot, C2
is unreachable and the gate's stopping rule should be read early.

Shell is HELD OUT and reported separately (the tuning rule). `mpc_tuesday` is
excluded from truth entirely: its two independent labels disagree by 25.4 px@640.

    backend/.venv/Scripts/python.exe eval/correspondence.py
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "eval"))

from swingvision.courtfit import DBL  # noqa: E402
from pencils import find_pencils, _homog  # noqa: E402

X_POS = (0.0, 1.37, 5.485, 9.60, 10.97)        # lengthwise lines, in metres
Y_POS = (0.0, 5.485, 11.885, 18.285, 23.77)    # across lines
TAU = 0.03              # pencil inlier tolerance, chosen on TUNE in step 1
N_PENCILS = 4
KEEP_PER_PENCIL = 4     # longest lines only; C(4,2)=6 pairs per pencil
EXCLUDE_TRUTH = {"mpc_tuesday_p01", "mpc_tuesday_p07"}


def _meet(l1, l2):
    """Intersection of two homogeneous lines as an (x, y) point, or None."""
    v = np.cross(l1, l2)
    if abs(v[2]) < 1e-9:
        return None                       # parallel in the image: no finite meet
    return float(v[0] / v[2]), float(v[1] / v[2])


def _quad_convex(pts):
    """FINITE ONLY. Convexity is not a valid requirement here, and demanding it was
    this solver's largest self-inflicted kill.

    A court is convex in the world, but a homography only preserves convexity when
    the shape does not cross the vanishing line. On a low mount the far baseline
    sits at or beyond the horizon, and the correct image of the court is then
    NON-convex - the far edge is "inverted" through infinity. Measured: requiring
    convexity of the four true line intersections rejected the TRUE correspondence
    on 10 of 30 tuning clips (`data/output/corr_attrib.json`), and low mounts are
    exactly the footage this project exists for. The shipped detector applies no
    such test, which is part of why it accepts `am_hard_utr` at a 1.74 m mount.

    Degenerate quads are still rejected - by the projected-corner floors, the pose
    prior, `verify_court` and the physical camera re-fit, all of which are shipped
    criteria and all of which run downstream of this."""
    p = np.asarray(pts, float)
    return bool(np.isfinite(p).all())


def _quad_ok(pts, w, h):
    """Convex, finite, and - when w/h are given - court-sized.

    THE SIZE FLOORS BELONG ON THE PROJECTED COURT, NOT ON THE CONSTRUCTION QUAD,
    and conflating the two was this solver's single biggest defect. The four
    intersections bound whatever sub-rectangle the chosen lines happen to enclose:
    label two lines x=0 and x=1.37 and they are 1.37 m apart, so a perfectly
    correct correspondence yields a legitimately narrow strip. Applying
    autodetect's 0.15w width floor to that strip rejected the TRUE correspondence
    on 10 of 30 tuning clips - the largest single kill in the attribution
    (`data/output/corr_attrib.json`), and self-inflicted.

    Pass w=h=0 (via `_quad_convex`) for the construction quad; pass the real frame
    size for the projected doubles corners, where the floors are autodetect's own
    and do mean something."""
    p = np.asarray(pts, float)
    if not np.isfinite(p).all():
        return False
    if w > 0 and p[:, 0].max() - p[:, 0].min() < 0.15 * w:
        return False                       # degeneracy floor on width
    if h > 0 and p[:, 1].max() - p[:, 1].min() < 0.06 * h:
        return False                       # and on depth
    # NO CONVEXITY TEST, on the corners either. Dropping it from the construction
    # quad alone moved the kill one stage later without saving a single clip -
    # 10 "not convex" became 11 "corner screen", survival unchanged at 7/30 - which
    # is what proved the projected COURT is the non-convex thing, not just the
    # sub-rectangle used to build it. A homography preserves convexity only when
    # the shape stays off the vanishing line, and a low mount puts the far baseline
    # on it. `autodetect`'s own degeneracy floor checks width and depth and nothing
    # else; this now matches it.
    return True


def solve_frame(im, calibration, court, cf, topn=8):
    """[(score, H, corners, assignment)] - the best labellings, best first."""
    dt, cos2, sin2, w, h, lines = cf._precompute(
        im, calibration, calibration.court_line_mask)
    if len(lines) < 4:
        return [], (dt, cos2, sin2, w, h, lines)
    tol = max(2.0, w * 0.006)
    L = _homog(lines)
    pens = find_pencils(lines, max_pencils=N_PENCILS, tau=TAU)
    if len(pens) < 2:
        return [], (dt, cos2, sin2, w, h, lines)

    wt = np.array([x[2] for x in lines], float)
    cands = []
    # every ORDERED pair of pencils: which family is lengthwise is itself unknown,
    # so both directions are tried and the score decides
    for pa, pb in itertools.permutations(range(len(pens)), 2):
        ia = sorted(pens[pa][1], key=lambda k: -wt[k])[:KEEP_PER_PENCIL]
        ib = sorted(pens[pb][1], key=lambda k: -wt[k])[:KEEP_PER_PENCIL]
        if len(ia) < 2 or len(ib) < 2:
            continue
        for la, lb in itertools.combinations(ia, 2):
            for lc, ld in itertools.combinations(ib, 2):
                P = [_meet(L[la], L[lc]), _meet(L[la], L[ld]),
                     _meet(L[lb], L[ld]), _meet(L[lb], L[lc])]
                if any(p is None for p in P) or not _quad_convex(P):
                    continue
                for xa, xb in itertools.combinations(X_POS, 2):
                    for yc, yd in itertools.combinations(Y_POS, 2):
                        # both orientations: the image order of a pencil's lines
                        # may be reversed relative to increasing world coordinate
                        for xs in ((xa, xb), (xb, xa)):
                            for ys in ((yc, yd), (yd, yc)):
                                world = [(xs[0], ys[0]), (xs[0], ys[1]),
                                         (xs[1], ys[1]), (xs[1], ys[0])]
                                try:
                                    H = calibration.compute_homography(world, P)
                                except Exception:
                                    continue
                                cands.append((H, (la, lb, lc, ld, xs, ys)))

    # --- score with the FULL shipped accept path, not a subset of it.
    #
    # A subset is not merely weaker here, it is circular: the hypothesis is BUILT
    # from four detected lines and `_ori_detail`/`_structure` reward landing on
    # detected lines, so the four that constructed it match by construction.
    # Measured, that let a labelling of two far-apart sidelines as x=0 and x=1.37
    # score g = 1.00 and st = 1.00 while sitting 2,245 px from truth - the enormous
    # stretch throws the rest of the court off-frame and nothing in g or st objects.
    #
    # The pose prior and the physical camera re-fit are exactly the terms that do
    # object, and they are shipped criteria, so the C-list permits them.
    prior = cf._load_prior()
    scored = []
    for H, asg in cands:
        try:
            corners = {n: calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                       for n in DBL}
        except Exception:
            continue
        c = np.array([corners[n] for n in DBL], float)
        if not np.isfinite(c).all() or not _quad_ok(c, w, h):
            continue
        # POSE FIRST - cheapest of the discriminating terms, and the one that kills
        # the stretched-court family outright
        p5 = cf._params_from_corners({n: c[i] for i, n in enumerate(DBL)})
        maha = cf._maha(p5, w, h, prior)
        g, nl, _ev = cf._ori_detail(H, calibration, court, dt, cos2, sin2,
                                    w, h, tol, 0.80)
        if g <= 0:
            continue
        st, st_m, _st_ev, n_ac, n_ln = cf._structure(H, lines, calibration,
                                                     dt, w, h, tol)
        if not (maha <= cf.PRIOR_MAHA_MAX
                or (st >= 0.70 and st_m >= 5 and n_ac >= 2 and n_ln >= 2)):
            continue
        scored.append([g * (0.5 + 0.5 * st), H,
                       {n: [float(corners[n][0]), float(corners[n][1])]
                        for n in DBL}, asg, g, st, st_m, n_ac, n_ln, maha])
    scored.sort(key=lambda t: -t[0])

    # the two expensive terms, on the shortlist only: a full-frame coverage check
    # and the physical re-fit that refuses a quad no real camera can produce
    out = []
    for row in scored[:60]:
        H = row[1]
        try:
            if not calibration.verify_court(im, H).ok:
                continue
        except Exception:
            continue
        if cf._cam_refine(im, row[2], calibration, court, dt, w, h) is None:
            continue
        out.append(tuple(row))
        if len(out) >= topn:
            break
    return out, (dt, cos2, sin2, w, h, lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=2)
    ap.add_argument("--clips", nargs="*")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from score_truth import truth_sources

    srcs = truth_sources(a.frames)
    if a.clips:
        srcs = [s for s in srcs if s[0] in set(a.clips)]
    print(f"{len(srcs)} clips, {a.frames} frames. Assignment and homography solved "
          f"TOGETHER.\nSub-bar: best-scoring candidate within 20 px@640 of the human "
          f"court, majority of TUNE.\n")
    print(f"{'clip':22s} {'cands':>6s} {'best_err':>9s} {'top1_err':>9s} "
          f"{'g':>5s} {'st':>5s} {'s':>5s}  labels(x|y)")
    print("-" * 92)

    rows, t0 = [], time.time()
    for clip, src, frames in srcs:
        per = []
        for _key, im, named in frames:
            if not all(n in named for n in DBL):
                continue
            scored, _pre = solve_frame(im, calibration, court, cf)
            w = im.shape[1]
            scale = 640.0 / w
            txy = np.array([named[n] for n in DBL], float)
            if not scored:
                per.append({"n": 0, "top1": None, "best": None,
                            "g": None, "st": None, "lab": "-"})
                continue

            def err(c):
                return float(np.mean(np.hypot(
                    *(np.array([c[n] for n in DBL], float) - txy).T))) * scale

            top1 = err(scored[0][2])
            best = min(err(s[2]) for s in scored)
            xs, ys = scored[0][3][4], scored[0][3][5]
            per.append({"n": len(scored), "top1": top1, "best": best,
                        "g": scored[0][4], "st": scored[0][5],
                        "s": scored[0][0],
                        "lab": f"{xs[0]:.2f},{xs[1]:.2f}|{ys[0]:.1f},{ys[1]:.1f}"})
        if not per:
            continue
        ok = [x for x in per if x["top1"] is not None]
        med = lambda k: (float(np.median([x[k] for x in ok])) if ok else None)  # noqa: E731
        row = {"clip": clip, "src": src, "excluded": clip in EXCLUDE_TRUTH,
               "shell": frames[0][1].shape[1] >= 3000,
               "n_cand": float(np.median([x["n"] for x in per])),
               "top1": med("top1"), "best": med("best"),
               "g": med("g"), "st": med("st"), "s": med("s"),
               "lab": ok[0]["lab"] if ok else "-", "frames": len(per)}
        rows.append(row)
        f = lambda x: "-" if x is None else f"{x:.1f}"     # noqa: E731
        g = lambda x: "-" if x is None else f"{x:.2f}"     # noqa: E731
        print(f"{row['clip']:22s} {row['n_cand']:6.0f} {f(row['best']):>9s} "
              f"{f(row['top1']):>9s} {g(row['g']):>5s} {g(row['st']):>5s} "
              f"{g(row['s']):>5s}  {row['lab']}", flush=True)

    print("-" * 92)
    live = [r for r in rows if not r["excluded"] and r["top1"] is not None]
    tune = [r for r in live if not r["shell"]]
    held = [r for r in live if r["shell"]]
    print(f"{len(rows)} clips in {time.time()-t0:.0f}s\n")
    for lab, pop in (("TUNE  (gold + 1920 refs)", tune), ("SHELL (held out)", held)):
        if not pop:
            continue
        t1 = sum(1 for r in pop if r["top1"] <= 20.0)
        bs = sum(1 for r in pop if r["best"] <= 20.0)
        print(f"{lab:26s} top-scoring within 20 px: {t1}/{len(pop)}   "
              f"(some candidate within 20 px: {bs}/{len(pop)})")
    if tune:
        t1 = sum(1 for r in tune if r["top1"] <= 20.0)
        print(f"\nPRE-REGISTERED SUB-BAR: majority of TUNE within 20 px.")
        print(f"  {t1}/{len(tune)} -> {'PASSES' if t1 > len(tune)/2 else 'FAILS'}")
        print("\n`best` minus `top1` is what better RANKING could buy. If `best` is "
              "good and\n`top1` is not, the solver constructs the court and the "
              "scorer mis-ranks it -\nwhich would be a NEW claim, since Session O "
              "measured the criteria recognising\nthe correct court on 19 of 20.")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
