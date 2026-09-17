"""court_map_ceiling.py - P8 C1: does the four-tap court model place every line?

WHY THIS EXISTS
---------------
Capability 1 (3D court mapping) says: from four tapped doubles corners plus the
regulation dimensions, place EVERY line and solve a 3D camera. Nothing had
measured it. P1 (tools/mono3d_ceiling.py) handed the ball fit a PERFECT court -
exact corners and the exact hfov - so every P1 number is conditional on a
perfect court model. This removes that condition, in simulation, before any
footage or court visit.

WHAT IT MEASURES, AND AGAINST WHAT
----------------------------------
A known camera (height_curve.frame_the_court: centre-line, 6 m setback, pitch
solved to frame the court) projects every court line exactly. The four corner
pixels are then perturbed by TAP noise, the model is rebuilt, and for points
sampled along every line we ask: a ball sitting exactly on that line appears at
its true pixel - where does the rebuilt model put it on the ground? The error is
taken PERPENDICULAR to the line, the component that changes a call.

Measured against EXACT geometry: the true court coordinates of the sampled line
points. No labels, no model output.

Two court maps are graded, because capability 1 feeds both:
  * "2d"  - calibration.homography_from_landmarks + image_to_court, the ground
            map the shipped line call uses. It does not use hfov at all.
  * "3d"  - bridge.camera_from_court_corners, the 6-DOF camera P1's 3D arm uses,
            intersected with z=0. It REQUIRES an hfov input (default 70 deg), so
            hfov error is swept for it.
What pins the model: the four coplanar corners, the regulation doubles rectangle
and - for the 3d map only - the assumed hfov.

Pre-registration: .claude/journals/lead.md, "P8". Bar: at the realistic tap
noise with exact hfov, p90 perpendicular error <= 5 cm on EVERY line, for BOTH
maps. Kill: any line > 10 cm at p90.

    cd backend && .venv/Scripts/python.exe ../tools/court_map_ceiling.py
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

from court_camera import CORNERS, HFOV_DEG, SETBACK_M, frame_the_court  # noqa: E402

W, H_IMG = 1920, 1080
HEIGHTS = (1.5, 3.0, 8.0)
# Human corner-click spread, published in STATE ("a court a median 5.8 px from
# the clicks", at 640 wide). Read as the median radial displacement of an
# isotropic 2-D Gaussian: sigma = 5.8 / sqrt(2 ln 2) = 4.93 px @640, then scaled
# by 1920/640. That scaling ASSUMES click precision is a fixed fraction of the
# frame, which a zoomed tap on a phone may beat - the sweep shows the curve.
HUMAN_SIGMA_1920 = 5.8 / math.sqrt(2 * math.log(2)) * (W / 640.0)
TAP_SIGMAS = (0.0, 1.0, 2.0, 4.0, round(HUMAN_SIGMA_1920, 2))
HFOV_ERRS = (0.0, -5.0, 5.0, -10.0, 10.0)
BAR_M, KILL_M = 0.05, 0.10


def lines():
    """Every painted line as (name, (x0,y0), (x1,y1), normal) in swingvision
    court metres. Near/far halves are separate lines, because the geometry says
    they behave differently."""
    from swingvision import court as C
    xl, xr = C.X_LEFT_DOUBLES, C.X_RIGHT_DOUBLES
    sl, sr, xc = C.X_LEFT_SINGLES, C.X_RIGHT_SINGLES, C.X_CENTER
    y0, ym, y1 = C.Y_NEAR_BASELINE, C.NET_Y, C.Y_FAR_BASELINE
    ns, fs = C.Y_NEAR_SERVICE, C.Y_FAR_SERVICE
    X, Y = (1.0, 0.0), (0.0, 1.0)
    out = []
    for half, (a, b) in (("near", (y0, ym)), ("far", (ym, y1))):
        out += [(f"{half}_doubles_sideline_L", (xl, a), (xl, b), X),
                (f"{half}_doubles_sideline_R", (xr, a), (xr, b), X),
                (f"{half}_singles_sideline_L", (sl, a), (sl, b), X),
                (f"{half}_singles_sideline_R", (sr, a), (sr, b), X)]
    out += [("near_centre_service", (xc, ns), (xc, ym), X),
            ("far_centre_service", (xc, ym), (xc, fs), X),
            ("near_baseline", (xl, y0), (xr, y0), Y),
            ("far_baseline", (xl, y1), (xr, y1), Y),
            ("near_service_line", (sl, ns), (sr, ns), Y),
            ("far_service_line", (sl, fs), (sr, fs), Y)]
    return out


def true_projector(height_m, pitch_deg, hfov_deg):
    """Pixel of any court-plane point, through the SAME physical camera
    frame_the_court solved (courtfit._cam_corners' convention, roll 0)."""
    f = (W / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)
    pitch = math.radians(pitch_deg)
    st, ct = math.sin(pitch), math.cos(pitch)
    fwd = np.array([0.0, ct, -st])
    right = np.array([1.0, 0.0, 0.0])
    up = np.array([0.0, st, ct])
    C = np.array([10.97 / 2.0, -SETBACK_M, height_m])

    def proj(xy):
        xy = np.atleast_2d(xy)
        d = np.column_stack([xy[:, 0] - C[0], xy[:, 1] - C[1],
                             np.full(len(xy), -C[2])])
        zc = d @ fwd
        return np.column_stack([W / 2.0 + f * (d @ right) / zc,
                                H_IMG / 2.0 - f * (d @ up) / zc])
    return proj


def ground_2d(corners):
    from swingvision import calibration
    Hm = calibration.homography_from_landmarks(corners)
    return lambda uv: calibration.image_to_court(Hm, uv)


def ground_3d(corners, hfov_deg):
    """Ray/z=0 intersection through the PnP camera, back in swingvision frame.
    Also returns the camera height the model believes."""
    from court_camera import camera_from_court_corners, to_court_xy
    cam, _ = camera_from_court_corners(corners, (W, H_IMG), hfov_deg=hfov_deg)
    c = np.asarray(cam.center, float)

    def fn(uv):
        r = cam.ray(np.asarray(uv, float))
        s = -c[2] / r[:, 2]
        g = c[None, :2] + s[:, None] * r[:, :2]
        return np.array([to_court_xy(p) for p in g])
    return fn, float(c[2])


def run(height_m, sigma, hfov_err, n, seed, n_pts=11):
    got = frame_the_court(height_m, SETBACK_M, HFOV_DEG, W, H_IMG)
    if got is None:
        return {"error": f"mount {height_m} m cannot frame the court"}
    kp, pitch = got
    proj = true_projector(height_m, pitch, HFOV_DEG)
    # The generator and the chain must agree about the camera, or every number
    # below is junk in a way no output reveals.
    for c in CORNERS:
        assert np.allclose(proj([_corner_xy(c)])[0], kp[c], atol=1e-6), c

    L = lines()
    samples = []
    for name, a, b, nrm in L:
        t = np.linspace(0.0, 1.0, n_pts)[:, None]
        xy = (1 - t) * np.array(a) + t * np.array(b)
        samples.append((name, xy, proj(xy), np.array(nrm)))

    rng = np.random.default_rng(seed)
    per = {m: {name: [] for name, *_ in L} for m in ("2d", "3d")}
    heights, fails = [], 0
    for _ in range(n):
        noisy = {c: (np.asarray(kp[c]) + rng.normal(0, sigma, 2)).tolist()
                 for c in CORNERS}
        g2 = ground_2d(noisy)
        try:
            g3, cz = ground_3d(noisy, HFOV_DEG + hfov_err)
        except RuntimeError:
            g3, fails = None, fails + 1        # no above-ground pose: a FAILURE
        if g3 is not None:
            heights.append(cz)
        for name, xy, uv, nrm in samples:
            e2 = np.abs((g2(uv) - xy) @ nrm)
            per["2d"][name].append(float(e2.max()))       # worst point on the line
            e3 = (np.abs((g3(uv) - xy) @ nrm).max() if g3 is not None
                  else float("inf"))
            per["3d"][name].append(float(e3))

    def summ(v):
        v = np.asarray(v)
        return {"p50": float(np.median(v)), "p90": float(np.percentile(v, 90))}
    out = {"height_m": height_m, "pitch_deg": pitch, "tap_sigma_px": sigma,
           "hfov_err_deg": hfov_err, "n": n, "seed": seed,
           "pose_failures": fails,
           "cam_height_p50": float(np.median(heights)) if heights else None,
           "cam_height_abs_err_p90": (float(np.percentile(
               np.abs(np.asarray(heights) - height_m), 90)) if heights else None),
           "maps": {}}
    for m in ("2d", "3d"):
        rows = {name: summ(v) for name, v in per[m].items()}
        worst = max(rows, key=lambda k: rows[k]["p90"])
        out["maps"][m] = {"lines": rows, "worst_line": worst,
                          "worst_p90": rows[worst]["p90"],
                          "pass": all(r["p90"] <= BAR_M for r in rows.values()),
                          "kill": any(r["p90"] > KILL_M for r in rows.values())}
    return out


def _corner_xy(name):
    from swingvision import court
    return court.LANDMARKS[name]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(REPO / "data/output/court_map_ceiling.json"))
    args = ap.parse_args()

    res = []
    for h in HEIGHTS:
        for s in TAP_SIGMAS:
            res.append(run(h, s, 0.0, args.n, args.seed))
        for e in HFOV_ERRS[1:]:
            for s in (0.0, TAP_SIGMAS[-1]):
                res.append(run(h, s, e, args.n, args.seed))
    Path(args.out).write_text(json.dumps(
        {"human_sigma_1920": HUMAN_SIGMA_1920, "bar_m": BAR_M, "kill_m": KILL_M,
         "measured_against": "exact court geometry through a known synthetic camera",
         "runs": res}, indent=1), encoding="utf-8")
    print(f"{'h':>4} {'tap':>6} {'hfov':>5} | {'2d worst p90':>13} {'line':<24}| "
          f"{'3d worst p90':>13} {'line':<24}| cam h p50  fail")
    for r in res:
        a, b = r["maps"]["2d"], r["maps"]["3d"]
        print(f"{r['height_m']:4.1f} {r['tap_sigma_px']:6.2f} {r['hfov_err_deg']:+5.0f} | "
              f"{a['worst_p90']:13.3f} {a['worst_line']:<24}| "
              f"{b['worst_p90']:13.3f} {b['worst_line']:<24}| "
              f"{r['cam_height_p50'] or float('nan'):7.2f} {r['pose_failures']:5d}")


if __name__ == "__main__":
    main()
