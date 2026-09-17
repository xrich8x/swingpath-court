"""eval/pencils.py - group the detected lines by CONCURRENCY, not by angle.

Step 1 of the joint line-to-model correspondence build
(`docs/evidence/court-correspondence-gate.md`). Nothing is proposed on top of this
until it is measured, because it is the exact primitive the previous branch got
wrong.

WHAT KILLED THE LAST ATTEMPT
-----------------------------
P3a split the detected lines into "baselines" and "sidelines" by DIRECTION. That is
ill-posed under perspective: the court's two doubles sidelines converge toward their
vanishing point, so they are not parallel in the image and form no angular cluster.
Measured, that split put 24 of 26 lines in one family on `am_hard_utr` while both
true sidelines sat in the detected set at 0.1 and 2.2 px.

The fix is not a better threshold. Lines that are parallel IN THE WORLD meet at a
common vanishing point in the image, whether or not they look parallel - so the
grouping question is "which lines are concurrent", and concurrency is exact
projective geometry rather than an angular guess.

A line in normal form (n, rho) is the homogeneous vector l = (cos n, sin n, -rho),
and a point v lies on it iff l . v = 0. So a pencil is a set of lines sharing a
common null vector, recoverable by RANSAC over line PAIRS: each pair proposes a
vanishing point, and the pencil is its inliers. Points at infinity fall out of the
same algebra with no special case - which matters, because a court shot square-on
has a genuinely infinite vanishing point and any (x, y) formulation would blow up.

THE BAR FOR THIS STEP, PRE-REGISTERED
--------------------------------------
The court has two world-parallel families: 5 lengthwise lines (at x = 0, 1.37,
5.485, 9.60, 10.97) and 5 across lines (y = 0, 5.485, 11.885, 18.285, 23.77). Using
the HUMAN homography to say which detected line is which, this step must

    (a) recover both true vanishing points, and
    (b) put the true lengthwise lines in one pencil and the true across lines in
        another, on a MAJORITY of the 40 clips.

If concurrency grouping also fails, the correspondence branch is in trouble and the
gate's stopping rule should be considered early rather than after a full build.

    backend/.venv/Scripts/python.exe eval/pencils.py
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

# The court's two world-parallel families, as (label, world endpoints).
LENGTHWISE = [("x=0.00", (0.0, 0.0), (0.0, 23.77)),
              ("x=1.37", (1.37, 0.0), (1.37, 23.77)),
              ("x=5.49", (5.485, 0.0), (5.485, 23.77)),
              ("x=9.60", (9.60, 0.0), (9.60, 23.77)),
              ("x=10.97", (10.97, 0.0), (10.97, 23.77))]
ACROSS = [("y=0.00", (0.0, 0.0), (10.97, 0.0)),
          ("y=5.49", (0.0, 5.485), (10.97, 5.485)),
          ("y=11.89", (0.0, 11.885), (10.97, 11.885)),
          ("y=18.29", (0.0, 18.285), (10.97, 18.285)),
          ("y=23.77", (0.0, 23.77), (10.97, 23.77))]

INLIER_TAU = 0.012      # normalised |l.v|; ~0.7 deg of pencil misalignment
MIN_PENCIL = 3          # a vanishing point needs 3 lines to be more than a pair
EXCLUDE_TRUTH = {"mpc_tuesday_p01", "mpc_tuesday_p07"}


def _homog(lines):
    """[(n, rho, w)] -> (N,3) homogeneous line vectors, unit-normed in (a, b)."""
    L = np.array([[np.cos(n), np.sin(n), -rho] for n, rho, _w in lines], float)
    return L


def _residual(L, v):
    """Normalised |l . v| for every line against one homogeneous point.

    Both sides are unit-normed so the residual is scale-free and comparable across
    finite and infinite vanishing points alike - the whole reason for staying in
    homogeneous coordinates instead of intersecting into (x, y)."""
    v = v / max(np.linalg.norm(v), 1e-12)
    ln = np.linalg.norm(L[:, :2], axis=1)
    return np.abs(L @ v) / np.maximum(ln, 1e-12)


def find_pencils(lines, max_pencils=2, tau=INLIER_TAU, exclusive=False):
    """[(vanishing_point, [line indices])] - the dominant concurrent families.

    Exhaustive over pairs rather than randomly sampled: with 16-40 lines that is at
    most ~800 candidates, cheap enough that RANSAC's sampling luck is not a variable
    anyone has to reason about later.

    NON-EXCLUSIVE BY DEFAULT, and that is a correction rather than a knob. The first
    version marked a pencil's inliers `used` and excluded them from later pencils.
    A line really does belong to only one world-parallel family, so that looked
    right - but the pencils are found GREEDILY, largest first, and in a cluttered
    frame the largest concurrent family is the building. Measured: capture of the
    true court lines was pinned at 2.0 of 3.5 lengthwise no matter whether 2, 4 or 6
    pencils were extracted, because the missing ones were being eaten by a clutter
    pencil that formed first, not left in an un-extracted one.

    Exclusivity is a decision about which family a line belongs to, and a greedy
    largest-first pass is not entitled to make it. The correspondence stage that
    consumes these has the court model and can decide; this function's job is only
    to report every concurrent family it can find. `exclusive=True` keeps the old
    behaviour for anyone who wants a hard partition."""
    if len(lines) < MIN_PENCIL:
        return []
    L = _homog(lines)
    wt = np.array([w for _n, _r, w in lines], float)
    n = len(L)
    used = np.zeros(n, bool)
    out = []

    for _ in range(max_pencils):
        best = (None, None, -1.0)
        for i in range(n):
            if used[i]:
                continue
            for j in range(i + 1, n):
                if used[j]:
                    continue
                v = np.cross(L[i], L[j])          # the two lines' meeting point
                if np.linalg.norm(v) < 1e-9:
                    continue                       # coincident lines
                r = _residual(L, v)
                inl = (r <= tau) & ~used
                if int(inl.sum()) < MIN_PENCIL:
                    continue
                # weight by line LENGTH, not count: three fence slats agreeing is
                # weaker evidence than three long painted lines agreeing.
                score = float(wt[inl].sum())
                if score > best[2]:
                    best = (v, np.flatnonzero(inl), score)
        if best[0] is None:
            break
        v, seed_inl, _s = best
        # re-fit the vanishing point on all its inliers (the null vector of their
        # stacked matrix) so it is not defined by the arbitrary seed pair
        _u, _s2, vt = np.linalg.svd(L[seed_inl])
        v = vt[-1]
        # membership is re-evaluated against the REFITTED point, over all lines
        full = np.flatnonzero(_residual(L, v) <= tau)
        out.append((v, full.tolist()))
        # only the seed's own inliers are retired, so the next pencil cannot be a
        # near-duplicate of this one while a shared line may still join both
        used[seed_inl] = True
        if exclusive:
            used[full] = True
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=2)
    ap.add_argument("--clips", nargs="*")
    ap.add_argument("--pencils", type=int, default=2,
                    help="how many concurrent families to extract")
    ap.add_argument("--tau", type=float, default=None)
    ap.add_argument("--min-pencil", type=int, default=None, dest="minp")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    global INLIER_TAU, MIN_PENCIL
    if a.tau is not None:
        INLIER_TAU = a.tau
    if a.minp is not None:
        MIN_PENCIL = a.minp

    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from score_truth import truth_sources

    srcs = truth_sources(a.frames)
    if a.clips:
        srcs = [s for s in srcs if s[0] in set(a.clips)]
    print(f"{len(srcs)} clips, {a.frames} frames. Grouping detected lines by "
          f"CONCURRENCY.\nTruth: which detected line is which, via the human "
          f"homography.\n")
    print(f"{'clip':22s} {'lines':>5s} {'pencils':>7s} {'len->P':>13s} "
          f"{'across->P':>13s}  verdict")
    print("-" * 84)

    rows, t0 = [], time.time()
    for clip, src, frames in srcs:
        per = []
        for _key, im, named in frames:
            if not all(n in named for n in DBL):
                continue
            _dt, _c2, _s2, w, h, lines = cf._precompute(
                im, calibration, calibration.court_line_mask)
            if len(lines) < MIN_PENCIL:
                continue
            scale = 640.0 / w
            H = calibration.compute_homography(
                [court.LANDMARKS[n] for n in DBL], [named[n] for n in DBL])
            pens = find_pencils(lines, max_pencils=a.pencils, tau=INLIER_TAU)

            # which detected line IS each true court line (nearest in normal form)
            def truth_members(fam):
                got = []
                for _lab, p0, p1 in fam:
                    pa = calibration.court_to_image(H, [p0])[0]
                    pb = calibration.court_to_image(H, [p1])[0]
                    n0, r0 = cf._norm_form(pa, pb)
                    best, bd = None, 1e18
                    for k, (ln, lr, _lw) in enumerate(lines):
                        dth = abs(np.mod(n0 - ln + np.pi / 2, np.pi) - np.pi / 2)
                        if dth <= np.deg2rad(6) and abs(r0 - lr) * scale < 8.0 \
                                and abs(r0 - lr) < bd:
                            best, bd = k, abs(r0 - lr)
                    if best is not None:
                        got.append(best)
                return got

            tl, ta = truth_members(LENGTHWISE), truth_members(ACROSS)

            def dominant(members):
                """(pencil index, how many of those true lines it holds)."""
                if not members or not pens:
                    return None, 0
                counts = [len(set(members) & set(idx)) for _v, idx in pens]
                k = int(np.argmax(counts))
                return k, counts[k]

            kl, cl = dominant(tl)
            ka, ca = dominant(ta)
            per.append({"n_lines": len(lines), "n_pen": len(pens),
                        "n_len_true": len(tl), "len_in": cl, "len_pen": kl,
                        "n_acr_true": len(ta), "acr_in": ca, "acr_pen": ka,
                        "separated": (kl is not None and ka is not None
                                      and kl != ka and cl >= 2 and ca >= 2)})
        if not per:
            continue
        med = lambda k: float(np.median([x[k] for x in per]))    # noqa: E731
        sep = sum(1 for x in per if x["separated"])
        row = {"clip": clip, "src": src, "excluded": clip in EXCLUDE_TRUTH,
               "shell": frames[0][1].shape[1] >= 3000,
               "n_lines": med("n_lines"), "n_pen": med("n_pen"),
               "len_in": med("len_in"), "n_len_true": med("n_len_true"),
               "acr_in": med("acr_in"), "n_acr_true": med("n_acr_true"),
               "len_pen": per[0]["len_pen"], "acr_pen": per[0]["acr_pen"],
               "separated": sep, "frames": len(per)}
        rows.append(row)
        v = "SEPARATED" if sep == len(per) else (
            f"{sep}/{len(per)} frames" if sep else "NOT separated")
        print(f"{clip:22s} {row['n_lines']:5.0f} {row['n_pen']:7.0f} "
              f"{row['len_in']:5.0f}/{row['n_len_true']:<4.0f} in P{row['len_pen'] if row['len_pen'] is not None else '-'}  "
              f"{row['acr_in']:5.0f}/{row['n_acr_true']:<4.0f} in P{row['acr_pen'] if row['acr_pen'] is not None else '-'}  "
              f"{v}", flush=True)

    print("-" * 84)
    live = [r for r in rows if not r["excluded"]]
    if not live:
        return
    full = sum(1 for r in live if r["separated"] == r["frames"])
    any_ = sum(1 for r in live if r["separated"] > 0)
    print(f"{len(rows)} clips in {time.time()-t0:.0f}s\n")
    print(f"the two true families land in DIFFERENT pencils, with >=2 members each:")
    print(f"  on every frame of the clip : {full}/{len(live)}")
    print(f"  on at least one frame      : {any_}/{len(live)}")
    print(f"median true lengthwise lines captured: "
          f"{np.median([r['len_in'] for r in live]):.1f} of "
          f"{np.median([r['n_len_true'] for r in live]):.1f}")
    print(f"median true across lines captured    : "
          f"{np.median([r['acr_in'] for r in live]):.1f} of "
          f"{np.median([r['n_acr_true'] for r in live]):.1f}")
    print(f"\nPRE-REGISTERED BAR for this step: separated on a MAJORITY of clips.")
    print(f"  {full}/{len(live)} -> {'PASSES' if full > len(live)/2 else 'FAILS'}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
