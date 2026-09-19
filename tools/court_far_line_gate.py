"""court_far_line_gate.py - can anything here SEE the far baseline? (G8)

WHY THIS EXISTS
---------------
qa's 2026-09-18 audit, section 7: `camera3d.paint_check` marks `far_baseline` and
`far_service` `unchecked` on 398 of 398 G7 trials, and the tracker therefore
reported `locked` while those two lines were 0.57-0.70 m out. This sets the two
thresholds of the new far-line instrument (`camera3d.far_line_stacks` +
`score_far_stacks`) the way G4 set the cross-ratio gate: a NOISE-ONLY sweep on
DEVELOPMENT seeds reporting the false-flag rate and the catch rate for every
value, then a score on seeds that played no part in it.

WHAT IT MEASURES, AND AGAINST WHAT
----------------------------------
The scene is `tools/court_track_sim.py`'s renderer in `subpixel=True` mode (CP1's
render order: jittered stratified sub-samples, PSF applied before binning). The
shipped `subpixel=False` order CANNOT render sub-pixel paint at all - see
`court_track_sim.SUBPIXEL_DEFAULT` for the measurements - so no far-line number
can be taken from it.

Truth is the exact synthetic camera that rendered the frame. For each frame a
LADDER of perturbed cameras is built by moving ONE thing (pitch, yaw, height,
depth) by a fixed list of magnitudes, both signs. The far-line ground error each
produces is MEASURED against the rendering camera and is the independent
variable; the instrument never sees it. The verdict scored is the whole
`paint_check.ok` - the flag the product acts on - not the far lines alone.

  GOOD  (false-flag population): every line within 10 cm (C1's KILL_M)
  WRONG (catch population):      a far line beyond 20 cm

THE SEARCH WINDOW IS PART OF THE INSTRUMENT
-------------------------------------------
G8 registered `reach = 3 * far_tol`. The code that produced the committed G8
tables carried a hard-coded 8.0 px @720 instead (qa, 2026-09-19), and that is not
a detail: the net tape sits 4.8-5.6 px from the far service line, inside the 8.0
window and outside the registered one. `--reach-mode registered` (the default)
couples the window to the tolerance cell by cell, for the stacked arm and the
pyramid arm alike; `--reach-mode fixed8` reproduces the committed G8 tables.

    cd backend && .venv/Scripts/python.exe ../tools/court_far_line_gate.py --seeds 300 301
    ... --reach-mode fixed8        # reproduce the G8 tables as published
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import court_track_sim as S                                        # noqa: E402
from swingvision import camera3d                                   # noqa: E402

OUT = REPO / "data" / "output" / "court_far_line_gate"


def _sha():
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                              text=True, timeout=15).stdout.strip() or "unknown"
    except Exception:
        return "unknown"

DEV_SEEDS = (300, 301, 302, 303, 304, 305)
SCORE_SEEDS = (400, 401, 402)
FAR = camera3d.FAR_LINES

# The perturbation LADDER. Magnitudes, not target errors: the far-line error each
# one produces is MEASURED against the rendering camera and is the independent
# variable in the analysis. Four motions, both signs, because the instrument is
# blind in one direction by construction - a pure yaw slides a cross-court line
# ALONG itself - and a one-motion sweep would hide that.
DEG = (0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.6)
MET = (0.01, 0.02, 0.05, 0.1, 0.25, 0.6, 1.5)
MOTIONS = {"pitch": DEG, "yaw": DEG, "height": MET, "depth": MET}
GOOD_M = 0.10          # C1's KILL_M: every line within 10 cm
WRONG_M = 0.20         # G8's catch population: a far line beyond 20 cm

TOL_GRID = (0.10, 0.15, 0.20, 0.25, 0.35, 0.50, 0.75, 1.00)
Z_GRID = (3.0, 4.0, 5.0, 6.0, 8.0)
# The window the profile is read over, per tolerance cell. "registered" is G8's
# own wording (3 x far_tol); "fixed8" is what the committed G8 run actually did.
REACH_FIXED_PX_720 = 8.0


def reach_for(tol, mode):
    return camera3d.FAR_REACH_MULT * tol if mode == "registered" else REACH_FIXED_PX_720


# the pyramid arm (the founder's literal proposal), swept on its own two knobs
PYR_TOL_GRID = TOL_GRID
PYR_DN_GRID = (2.0, 3.0, 4.0, 6.0, 9.0)


# ------------------------------------------------------------- the ladder --
def _move(p0, motion, mag):
    """One perturbed camera. `mag` is degrees for the two angles, metres else."""
    if motion == "pitch":
        return S.camera(0.0, p0 + math.radians(mag), 0.0)
    if motion == "yaw":
        return S.camera(math.radians(mag), p0, 0.0)
    if motion == "height":
        return S.camera(0.0, p0, 0.0, dz=mag)
    if motion == "depth":
        return S.camera(0.0, p0, 0.0, dy=mag)
    raise ValueError(motion)


# G8's registered definition: "the worse of far_baseline / far_service, either
# half, as C1 measures them". C1 calls them `far_baseline` and `far_service_line`.
# The far HALVES of the sidelines are a blind spot too and are reported beside it,
# but they are not what the bar is written against.
FAR_C1 = ("far_baseline", "far_service_line")


def _errs(true_cam, cam):
    e = S.line_errors(true_cam, cam.ground_point)
    far = max(e[k] for k in FAR_C1)
    far_half = max(v for k, v in e.items() if k.startswith("far"))
    return far, far_half, max(e.values())


def ladder(true_cam, p0):
    """[(camera, motion, magnitude)] - the truth plus every perturbation."""
    out = [(true_cam, "none", 0.0)]
    for motion, mags in MOTIONS.items():
        for m in mags:
            for sgn in (1, -1):
                out.append((_move(p0, motion, sgn * m), motion, sgn * m))
    return out


# --------------------------------------------------------- the pyramid arm -
def pyramid_far(grey, cam, *, levels=3, tol_px_720=0.20, min_dn=6.0,
                min_width_px_720=0.67, clear_m=0.3, min_frac_det=0.5,
                reach_px_720=8.0):
    """The founder's literal proposal, measured as a declared secondary arm: run
    `ridge_offsets` on each level of a 3-level Gaussian pyramid at the far-line
    points and keep the level that FINDS the most ridges. Reported at level-0
    pixels so the numbers are comparable with the stacked profile."""
    import cv2
    s_scale = cam.image_wh[1] / 720.0
    tol = tol_px_720 * s_scale
    pyr = [np.asarray(grey, float)]
    for _ in range(levels - 1):
        pyr.append(cv2.pyrDown(pyr[-1]))
    w, h = cam.image_wh
    out = {}
    for name, width, world, wdir in camera3d._far_dense(clear_m):
        uv = cam.project(world)
        inb = (np.isfinite(uv).all(1) & (uv[:, 0] >= 8) & (uv[:, 0] < w - 8)
               & (uv[:, 1] >= 8) & (uv[:, 1] < h - 8))
        if inb.sum() < 24:
            continue
        n3 = np.column_stack([-wdir[inb, 1], wdir[inb, 0], np.zeros(int(inb.sum()))])
        wpx = np.linalg.norm(cam.project(world[inb] + n3 * width / 2)
                             - cam.project(world[inb] - n3 * width / 2), axis=1)
        idx = np.flatnonzero(inb)[wpx < min_width_px_720 * s_scale]
        if len(idx) < 24:
            continue
        # ~1 px apart at level 0, as the stacked arm samples
        pxy = uv[idx]
        d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pxy, axis=0), axis=1))]
        keep = [0]
        for i in range(1, len(d)):
            if d[i] - d[keep[-1]] >= s_scale:
                keep.append(i)
        idx = idx[np.array(keep)]
        nrm = camera3d.line_normals(cam, world[idx], wdir[idx])
        best = None
        for lv, im in enumerate(pyr):
            sc = 2.0 ** lv
            # the same absolute search window as the stacked arm, so the two
             # differ only in mechanism
            off, found = camera3d.ridge_offsets(im, uv[idx] / sc, nrm,
                                                reach_px_720 * s_scale / sc, min_dn)
            off = off * sc                       # back to level-0 pixels
            if best is None or found.sum() > best[0]:
                best = (int(found.sum()), lv, off, found)
        n_det, lv, off, found = best
        seen = n_det >= max(1, int(math.ceil(min_frac_det * len(idx))))
        hits = found & (np.abs(off) <= tol)
        out[name] = {"frac": float(hits.sum() / n_det) if n_det else 0.0,
                     "seen": bool(seen), "level": lv, "n_det": n_det,
                     "n_samples": int(len(idx))}
    return out


# ------------------------------------------------------------------ cases --
def cases(seed, ss, verbose=True, reach_mode="registered"):
    """Every ladder case for one seed, scored on every threshold pair. The verdict
    is the WHOLE `paint_check`, not the far lines alone - the G8 bar is "reported
    NOT locked", and the near lines are part of that."""
    rng = np.random.default_rng(seed)
    p0 = S.base_pitch()
    true_cam = S.camera(0.0, p0, 0.0)
    t0 = time.time()
    img = np.clip(S.render(true_cam, rng, ss=ss, subpixel=True), 0, 255).astype(np.uint8)
    t_render = time.time() - t0
    rows = []
    for cam, motion, mag in ladder(true_cam, p0):
        far_err, far_half_err, worst_err = _errs(true_cam, cam)
        base = camera3d.paint_check(img, cam, far_lines=False)
        row = {"seed": seed, "motion": motion, "mag": mag, "far_err_m": far_err,
               "far_half_err_m": far_half_err,
               "worst_err_m": worst_err, "pre_g8_ok": bool(base.ok),
               "pre_g8_unchecked": list(base.unchecked),
               "stack": {}, "pyramid": {}}
        for tol in TOL_GRID:
            for z in Z_GRID:
                # `far_lines=True` is LOAD-BEARING: camera3d.FAR_LINES_DEFAULT is
                # False, so without it this tool scores the pre-G8 check in every
                # cell and the sweep measures nothing (qa, 2026-09-19, fault A).
                c = camera3d.paint_check(img, cam, far_lines=True,
                                         far_kw={"far_tol_px_720": tol,
                                                 "far_min_z": z,
                                                 "reach_px_720": reach_for(tol, reach_mode)})
                far_flag = any(c.detail.get(nm, {}).get("thin", (1.0,))[0] < 0.5
                               for nm in FAR)
                row["stack"][f"{tol}|{z}"] = [bool(c.ok), bool(far_flag),
                                              sorted(set(c.unchecked) & set(FAR))]
        for tol in PYR_TOL_GRID:
            for dn in PYR_DN_GRID:
                v = pyramid_far(img, cam, tol_px_720=tol, min_dn=dn,
                                reach_px_720=reach_for(tol, reach_mode))
                seen_far = [nm for nm in FAR if v.get(nm, {}).get("seen")]
                far_flag = any(v[nm]["frac"] < 0.5 for nm in seen_far)
                ok = bool(base.ok) and not far_flag
                row["pyramid"][f"{tol}|{dn}"] = [ok, bool(far_flag),
                                                 sorted(set(FAR) - set(seen_far))]
        rows.append(row)
        if verbose:
            print(f"  seed {seed} {motion:7s} {mag:+7.3f} far {far_err * 100:8.2f} cm "
                  f"worst {worst_err * 100:8.2f} cm pre-G8 ok={base.ok} "
                  f"({time.time() - t0:.0f}s)", flush=True)
    return rows, t_render


# ---------------------------------------------------------------- scoring --
def rates(rows, arm, key):
    """CATCH is on `paint_check.ok`, the flag the product acts on. FALSE is the
    INCREMENTAL false-flag rate, over the good cases the pre-G8 check already
    passed: G8's bar says a frame already failing on a near line is not a
    far-line false flag and is counted separately (`false_total`)."""
    nw = ng = nb = catch = false = false_tot = unseen = 0
    for r in rows:
        ok, _far_flag, unchecked = r[arm][key]
        if r["far_err_m"] > WRONG_M:
            nw += 1
            catch += not ok
        elif r["worst_err_m"] <= GOOD_M:
            ng += 1
            false_tot += not ok
            unseen += bool(unchecked)
            if r["pre_g8_ok"]:
                nb += 1
                false += not ok
    nan = float("nan")
    return {"catch": catch / nw if nw else nan, "false": false / nb if nb else nan,
            "false_total": false_tot / ng if ng else nan, "n_wrong": nw, "n_good": ng,
            "n_good_pre_g8_ok": nb,
            "far_unchecked_on_good": unseen / ng if ng else nan}


def sweep_table(rows, arm, tols, second):
    out = []
    for tol in tols:
        for s2 in second:
            r = rates(rows, arm, f"{tol}|{s2}")
            out.append({"tol_px_720": tol, "second": s2, **r})
    return out


def choose(table):
    """G8's rule, fixed before the run: the highest catch among pairs whose
    development false-flag rate is <= 1%; ties to the LARGER tolerance."""
    ok = [r for r in table if r["false"] <= 0.01 and np.isfinite(r["catch"])]
    if not ok:
        return None
    best = max(r["catch"] for r in ok)
    return max([r for r in ok if r["catch"] >= best - 1e-12],
               key=lambda r: r["tol_px_720"])


def baseline(rows):
    """What the PRE-G8 check does on the same population - the control arm."""
    nw = ng = catch = false = 0
    for r in rows:
        if r["far_err_m"] > WRONG_M:
            nw += 1
            catch += not r["pre_g8_ok"]
        elif r["worst_err_m"] <= GOOD_M:
            ng += 1
            false += not r["pre_g8_ok"]
    return {"catch": catch / nw if nw else float("nan"),
            "false": false / ng if ng else float("nan"), "n_wrong": nw, "n_good": ng}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=int, nargs="+", default=list(DEV_SEEDS))
    ap.add_argument("--ss", type=int, default=2)
    ap.add_argument("--tag", default="dev")
    ap.add_argument("--reach-mode", choices=("registered", "fixed8"), default="registered",
                    help="registered = G8's own 3 x far_tol; fixed8 = the 8.0 px @720 "
                         "the committed G8 run used")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows, t_render = [], []
    for s in a.seeds:
        r, tr = cases(s, a.ss, reach_mode=a.reach_mode)
        rows += r
        t_render.append(tr)
    st = sweep_table(rows, "stack", TOL_GRID, Z_GRID)
    py = sweep_table(rows, "pyramid", PYR_TOL_GRID, PYR_DN_GRID)
    res = {"stamp": {"tool": "tools/court_far_line_gate.py", "seeds": a.seeds,
                     "commit": _sha(),
                     "ss": a.ss, "subpixel": True, "tag": a.tag,
                     "reach_mode": a.reach_mode,
                     "reach_px_720": ("3 x tol per cell" if a.reach_mode == "registered"
                                      else REACH_FIXED_PX_720),
                     "far_lines": True,
                     "render_s_p50": float(np.median(t_render)),
                     "measured_against": "the exact synthetic camera that rendered "
                                         "each frame; the ladder target is the "
                                         "independent variable",
                     "good": f"every line within {GOOD_M} m",
                     "wrong": f"a far line > {WRONG_M} m",
                     "min_line_frac": 0.5},
           "pre_g8_baseline": baseline(rows),
           "stack_sweep": st, "pyramid_sweep": py,
           "stack_choice": choose(st), "pyramid_choice": choose(py),
           "rows": rows}
    out = Path(a.out or OUT / f"{a.tag}_seeds{'-'.join(map(str, a.seeds))}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for nm, tab, ch in (("STACK", st, res["stack_choice"]),
                        ("PYRAMID", py, res["pyramid_choice"])):
        print(f"\n=== {nm} ===")
        print(f"{'tol@720':>8}{'z/dn':>6}{'catch':>8}{'false':>8}{'falseTot':>9}"
              f"{'unchk_good':>12}")
        for r in tab:
            print(f"{r['tol_px_720']:8.2f}{r['second']:6.1f}{r['catch']:8.3f}"
                  f"{r['false']:8.3f}{r['false_total']:9.3f}"
                  f"{r['far_unchecked_on_good']:12.3f}")
        print("chosen:", ch)
    print("pre-G8 baseline:", res["pre_g8_baseline"])
    print("wrote", out)


if __name__ == "__main__":
    main()
