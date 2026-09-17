"""eval/corr_attrib.py - which term discards the TRUE court inside the joint solver?

`eval/correspondence.py` returns ZERO candidates on 19 of 38 clips, including
`am_ntrp40`, which the shipped detector accepts at 7.9 px. Something is filtering
out courts that demonstrably work, and "something" has four candidates with four
different fixes:

    the PENCILS never supply two usable lines in each family
    the QUAD screens (convexity, width/depth floors) reject the intersections
    the POSE prior or `verify_court` rejects the projected court
    `_cam_refine` refuses it as physically impossible

Guessing between them is how the last five branches were spent. This measures it,
in the shape `eval/seed_reach.py` used for the lattice: hand the solver the
correspondence the HUMAN homography says is correct, and follow that one candidate
through every screen in the order the solver applies them.

The candidate here is not a search result - it is the true answer, constructed from
the detected lines that really are the court's lines and labelled with the model
positions they really have. If it dies, whatever kills it is discarding the truth,
and that term is the fix target.

Ground truth is human only. Shell is reported separately; `mpc_tuesday` is excluded
(its two labels disagree by 25.4 px@640).

    backend/.venv/Scripts/python.exe eval/corr_attrib.py
"""

from __future__ import annotations

import argparse
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
from correspondence import (_meet, _quad_ok, _quad_convex,
                            X_POS, Y_POS, TAU, N_PENCILS)  # noqa: E402

# The court's real lines, paired with the model coordinate they sit at.
LENGTHWISE = [(x, (x, 0.0), (x, 23.77)) for x in X_POS]
ACROSS = [(y, (0.0, y), (10.97, y)) for y in Y_POS]

STAGES = ("pencil supply", "two pencils", "no intersection", "not convex",
          "homography failed", "corner screen", "pose", "g>0", "verify",
          "camera re-fit")
EXCLUDE_TRUTH = {"mpc_tuesday_p01", "mpc_tuesday_p07"}


def _match_line(n0, r0, lines, scale, ang_deg=6.0, rho640=8.0):
    """Index of the detected line that IS this projected court line, or None."""
    best, bd = None, 1e18
    for k, (ln, lr, _lw) in enumerate(lines):
        dth = abs(np.mod(n0 - ln + np.pi / 2, np.pi) - np.pi / 2)
        if dth <= np.deg2rad(ang_deg) and abs(r0 - lr) * scale <= rho640 \
                and abs(r0 - lr) < bd:
            best, bd = k, abs(r0 - lr)
    return best


def trace(im, named, calibration, court, cf):
    """Follow the TRUE correspondence through every screen. Returns a dict."""
    dt, cos2, sin2, w, h, lines = cf._precompute(
        im, calibration, calibration.court_line_mask)
    tol = max(2.0, w * 0.006)
    scale = 640.0 / w
    out = {"n_lines": len(lines), "died": None}
    if len(lines) < 4:
        out["died"] = "pencil supply"
        return out

    H_true = calibration.compute_homography(
        [court.LANDMARKS[n] for n in DBL], [named[n] for n in DBL])

    # which detected line is each true court line, and at what model coordinate
    def found(fam):
        got = []
        for coord, p0, p1 in fam:
            pa = calibration.court_to_image(H_true, [p0])[0]
            pb = calibration.court_to_image(H_true, [p1])[0]
            n0, r0 = cf._norm_form(pa, pb)
            k = _match_line(n0, r0, lines, scale)
            if k is not None:
                got.append((coord, k))
        return got

    fl, fa = found(LENGTHWISE), found(ACROSS)
    out["n_len"], out["n_acr"] = len(fl), len(fa)
    if len(fl) < 2 or len(fa) < 2:
        out["died"] = "pencil supply"      # not enough of the court was detected
        return out

    # do the concurrency pencils actually separate them?
    pens = find_pencils(lines, max_pencils=N_PENCILS, tau=TAU)
    out["n_pen"] = len(pens)
    if len(pens) < 2:
        out["died"] = "two pencils"
        return out
    pl = [p for p, (_v, idx) in enumerate(pens)
          if len(set(k for _c, k in fl) & set(idx)) >= 2]
    pa_ = [p for p, (_v, idx) in enumerate(pens)
           if len(set(k for _c, k in fa) & set(idx)) >= 2]
    out["sep"] = bool(pl and pa_ and set(pl) != set(pa_))
    if not out["sep"]:
        out["died"] = "two pencils"        # families not separated into pencils
        return out

    # build the TRUE candidate: two real lengthwise lines at their real x, two
    # real across lines at their real y. This is the answer, not a hypothesis.
    L = _homog(lines)
    (xa, la), (xb, lb) = fl[0], fl[-1]
    (yc, lc), (yd, ld) = fa[0], fa[-1]
    P = [_meet(L[la], L[lc]), _meet(L[la], L[ld]),
         _meet(L[lb], L[ld]), _meet(L[lb], L[lc])]
    if any(p is None for p in P):
        out["died"] = "no intersection"
        return out
    if not _quad_convex(P):
        out["died"] = "not convex"
        return out
    world = [(xa, yc), (xa, yd), (xb, yd), (xb, yc)]
    try:
        H = calibration.compute_homography(world, P)
    except Exception:
        out["died"] = "homography failed"
        return out

    corners = {n: calibration.court_to_image(H, [court.LANDMARKS[n]])[0] for n in DBL}
    c = np.array([corners[n] for n in DBL], float)
    txy = np.array([named[n] for n in DBL], float)
    out["err"] = float(np.mean(np.hypot(*(c - txy).T))) * scale
    if not np.isfinite(c).all() or not _quad_ok(c, w, h):
        out["died"] = "corner screen"
        return out

    prior = cf._load_prior()
    p5 = cf._params_from_corners({n: c[i] for i, n in enumerate(DBL)})
    maha = cf._maha(p5, w, h, prior)
    g, _nl, _ev = cf._ori_detail(H, calibration, court, dt, cos2, sin2,
                                 w, h, tol, 0.80)
    st, st_m, _se, n_ac, n_ln = cf._structure(H, lines, calibration, dt, w, h, tol)
    out.update({"maha": float(maha), "g": float(g), "st": float(st)})
    if not (maha <= cf.PRIOR_MAHA_MAX
            or (st >= 0.70 and st_m >= 5 and n_ac >= 2 and n_ln >= 2)):
        out["died"] = "pose"
        return out
    if g <= 0:
        out["died"] = "g>0"
        return out
    try:
        if not calibration.verify_court(im, H).ok:
            out["died"] = "verify"
            return out
    except Exception:
        out["died"] = "verify"
        return out
    if cf._cam_refine(im, {n: [float(c[i][0]), float(c[i][1])]
                           for i, n in enumerate(DBL)},
                      calibration, court, dt, w, h) is None:
        out["died"] = "camera re-fit"
        return out
    return out            # survived every screen


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=1)
    ap.add_argument("--clips", nargs="*")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from score_truth import truth_sources

    srcs = truth_sources(a.frames)
    if a.clips:
        srcs = [s for s in srcs if s[0] in set(a.clips)]
    print(f"{len(srcs)} clips. Handing the solver the TRUE correspondence and "
          f"following it\nthrough every screen, in the order the solver applies "
          f"them.\n")
    print(f"{'clip':22s} {'lines':>5s} {'len/acr':>8s} {'err':>7s} {'maha':>6s} "
          f"{'g':>5s} {'st':>5s}  died at")
    print("-" * 84)

    rows, t0 = [], time.time()
    for clip, src, frames in srcs:
        for _key, im, named in frames:
            if not all(n in named for n in DBL):
                continue
            r = trace(im, named, calibration, court, cf)
            r.update({"clip": clip, "src": src,
                      "shell": im.shape[1] >= 3000,
                      "excluded": clip in EXCLUDE_TRUTH})
            rows.append(r)
            f = lambda k, p=".1f": ("-" if r.get(k) is None else f"{r[k]:{p}}")  # noqa: E731
            print(f"{clip:22s} {r['n_lines']:5d} "
                  f"{r.get('n_len', 0):3d}/{r.get('n_acr', 0):<4d} "
                  f"{f('err'):>7s} {f('maha'):>6s} {f('g', '.2f'):>5s} "
                  f"{f('st', '.2f'):>5s}  {r['died'] or 'SURVIVED'}", flush=True)
            break

    print("-" * 84)
    live = [r for r in rows if not r["excluded"]]
    print(f"{len(rows)} clips in {time.time()-t0:.0f}s\n")
    from collections import Counter
    for lab, pop in (("TUNE (gold + 1920)", [r for r in live if not r["shell"]]),
                     ("SHELL (held out)", [r for r in live if r["shell"]])):
        if not pop:
            continue
        c = Counter(r["died"] or "SURVIVED" for r in pop)
        print(f"{lab} - {len(pop)} clips")
        for st in ("SURVIVED",) + STAGES:
            if c.get(st):
                print(f"    {st:16s} {c[st]:3d}  {'#' * c[st]}")
        print()
    surv = [r for r in live if r["died"] is None and r.get("err") is not None]
    if surv:
        print(f"where the TRUE correspondence survives, its error is a median "
              f"{np.median([r['err'] for r in surv]):.1f} px@640 "
              f"(n={len(surv)}).")
    print("The stage killing the most clips is the fix target. If the kills are "
          "spread,\nno single change rescues the solver.")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
