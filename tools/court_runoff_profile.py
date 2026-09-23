"""court_runoff_profile.py - does the tracking sim's run-off step reach the far baseline?

Job 1 of the 2026-09-23 handoff. `court_track_sim.render(runoff_dn=...)` paints the
ground outside the outer lines darker, as CP1 does (95 court / 80 run-off). This
renders ONE frame through the exact camera G9 and G8 use (1920x1080, hfov 100,
3.0 m mount, 6.0 m setback, base pitch), with and without the step, and reports:

  * the far baseline's stacked normal profile (`camera3d.far_line_stacks`, the
    far-line instrument's own measurement) over a WIDE window, so the step itself
    is visible, not just the ridge;
  * where the ridge sits on every line, against the true camera's prediction:
    the stacked-profile peak for the thin far lines (`camera3d._seg_hit`, the
    instrument's own peak rule) and the median per-point `ridge_offsets` for the
    wide lines (`paint_check`'s own measurement).

Measured against the exact synthetic camera that rendered the frame. Nothing is
fitted and nothing is scored against its own output: the camera IS the truth.

    python tools/court_runoff_profile.py            # noiseless and noisy, ss 2 and 4
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import court_track_sim as S                                        # noqa: E402
from swingvision import camera3d                                   # noqa: E402

OUT = REPO / "data" / "output" / "court_runoff_profile"
WIDE_REACH_PX_720 = 8.0     # wide enough to show the step; a DISPLAY window, not a check
STEP_WING_PX = 4.0          # |s| beyond this (px @1080) is read as the plain ground level


def _sha():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                              text=True, timeout=15).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def measure(img, cam):
    s_scale = cam.image_wh[1] / 720.0
    tol = camera3d.FAR_TOL_PX_720 * s_scale
    out = {"thin": {}, "wide": {}}
    st = camera3d.far_line_stacks(img, cam, reach_px_720=WIDE_REACH_PX_720)
    for name, (sv, profs, n) in st.items():
        segs = [camera3d._seg_hit(sv, P, tol, 0.0) for P in profs]
        pooled = np.mean(profs, 0)
        lo, hi = pooled[sv < -STEP_WING_PX], pooled[sv > STEP_WING_PX]
        out["thin"][name] = {
            "n_samples": n, "n_seg": len(profs),
            "peak_off_px_per_seg": [round(o, 4) if np.isfinite(o) else None
                                    for _, _, _, o in segs],
            "pooled_peak_off_px": round(float(sv[int(np.argmax(pooled))]), 3),
            "ground_dn_below": round(float(lo.mean()), 3) if len(lo) else None,
            "ground_dn_above": round(float(hi.mean()), 3) if len(hi) else None,
            "peak_dn": round(float(pooled.max()), 3),
            "s_px": [round(float(x), 3) for x in sv],
            "pooled_profile": [round(float(x), 3) for x in pooled]}
    world, wdir, ids, names, widths = camera3d._samples(0.4)
    uv = cam.project(world)
    w, h = cam.image_wh
    inb = (np.isfinite(uv).all(1) & (uv[:, 0] >= 8) & (uv[:, 0] < w - 8)
           & (uv[:, 1] >= 8) & (uv[:, 1] < h - 8))
    n3 = np.column_stack([-wdir[:, 1], wdir[:, 0], np.zeros(len(wdir))])
    wpx = np.zeros(len(world))
    wpx[inb] = np.linalg.norm(cam.project(world[inb] + n3[inb] * (widths[ids[inb]] / 2)[:, None])
                              - cam.project(world[inb] - n3[inb] * (widths[ids[inb]] / 2)[:, None]),
                              axis=1)
    use = inb & (wpx >= 0.67 * s_scale)
    nrm = np.zeros_like(uv)
    nrm[use] = camera3d.line_normals(cam, world[use], wdir[use])
    off, found = camera3d.ridge_offsets(img, uv[use], nrm[use], 3.0 * 1.5 * s_scale, 6.0)
    lid = ids[use]
    for i, nm in enumerate(names):
        m = (lid == i) & found
        if m.sum() >= 6:
            out["wide"][nm] = {"n": int(m.sum()), "median_off_px": round(float(np.median(off[m])), 4)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ss", type=int, nargs="+", default=[2, 4])
    ap.add_argument("--runoff-dn", type=float, default=S.RUNOFF_DN_CP1)
    ap.add_argument("--seed", type=int, default=0, help="noise draw only; the camera is fixed")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cam = S.camera(0.0, S.base_pitch(), 0.0)
    res = {"stamp": {"tool": "tools/court_runoff_profile.py", "commit": _sha(),
                     "camera": "court_track_sim base pose (G8/G9 geometry), exact truth",
                     "subpixel": True, "runoff_dn": a.runoff_dn, "surface_dn": S.SURFACE_DN,
                     "wide_reach_px_720": WIDE_REACH_PX_720, "noise_seed": a.seed,
                     "offset_sign": "+ along camera3d.line_normals of the TRUE projection",
                     "measured_against": "the exact synthetic camera that rendered the frame"},
           "cells": []}
    for ss in a.ss:
        for noise in (False, True):
            for ro in (None, a.runoff_dn):
                img = np.clip(S.render(cam, np.random.default_rng(a.seed), noise=noise, ss=ss,
                                       subpixel=True, runoff_dn=ro), 0, 255)
                m = measure(img, cam)
                res["cells"].append({"ss": ss, "noise": noise, "runoff_dn": ro, **m})
                fb = m["thin"].get("far_baseline", {})
                print(f"ss {ss} noise {noise!s:5s} runoff {ro!s:5s} far_baseline: pooled peak "
                      f"{fb.get('pooled_peak_off_px')} px, segs {fb.get('peak_off_px_per_seg')}, "
                      f"ground {fb.get('ground_dn_below')} | {fb.get('ground_dn_above')} DN, "
                      f"peak {fb.get('peak_dn')}", flush=True)
                fs = m["thin"].get("far_service", {})
                print(f"    far_service segs {fs.get('peak_off_px_per_seg')}")
                print("    wide lines median ridge offset px: "
                      + ", ".join(f"{k} {v['median_off_px']:+.3f}" for k, v in m["wide"].items()))
    out = Path(a.out or OUT / "runoff_profile.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
