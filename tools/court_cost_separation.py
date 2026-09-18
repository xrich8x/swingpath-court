"""court_cost_separation.py - G7: does a photometric cost separate a RIGHT camera
from a WRONG one?

Re-runs CP1 arm P / camera3d arm K (21 noisy 3D keypoints -> camera3d.solve_pnp_seed
-> paintfit.r1_fit, principal point at the image centre) and, on the SAME image the
fit saw, measures three quantities for the FITTED camera and two of them for the
TRUE camera (tools/court_fit_cp1.py::truth_camera, the exact rendering camera, which
is independent of the fit - hard rule 1):

  (1) camera3d.paint_check at its shipped defaults: court-wide support, per-line
      fractions, worst line, ok flag, unchecked lines;
  (2) the RIDGE RESIDUAL defined in docs/evidence/court-camera3d.md G7: the
      censored distance, in px @720, from each projected paint-centreline sample to
      the nearest bright ridge along its line's normal, searched within +-12 px @720
      and scored as the full 12 px when no ridge is found;
  (3) the fit's OWN final robust cost - a self-consistency number, not evidence.

The wrong/right label is RECOMPUTED from the fit actually scored (|f_fit - f_true| /
f_true > 1%), because this harness's libx265 is not deterministic run to run.

The bar, the split and the null control are pre-registered in
docs/evidence/court-camera3d.md, section G7, committed before this ran.

    .venv/Scripts/python.exe tools/court_cost_separation.py --n 400 --seed 0
    .venv/Scripts/python.exe tools/court_cost_separation.py --analyse <rows.json>
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import court_fit_cp1 as T                                          # noqa: E402
from swingvision import camera3d, court, paintfit                  # noqa: E402

OUT_DIR = REPO / "data" / "output" / "court_cost_separation"
N_OUTLIERS = 2
OUTLIER_PX = (100.0, 300.0)

# ---- G7 instrument (2), fixed here and stated in the evidence file ----------
RIDGE_REACH_PX_720 = 12.0      # search half-width; a miss scores the full reach
RIDGE_MIN_DN = 6.0             # a ridge must stand this far above the profile median
RIDGE_MIN_WIDTH_PX_720 = 0.67  # paint_check's own width filter -> same far-line blind spot
RIDGE_STEP_M = 0.4             # paint_check's own sample spacing
WRONG_F_REL = 0.01             # G1's wrong-camera rule


def ridge_residual(grey, cam, *, reach_px_720=RIDGE_REACH_PX_720, min_dn=RIDGE_MIN_DN,
                   min_width_px_720=RIDGE_MIN_WIDTH_PX_720, step_m=RIDGE_STEP_M):
    """G7 instrument (2). Censored distance-to-nearest-ridge along the projected
    painted lines, in px @720. Same samples, same ridge finder and the same
    width filter as camera3d.paint_check - so the same far-line blind spot - but
    censored at a wider reach instead of thresholded, so a wrong camera is graded
    rather than saturated."""
    world, wdir, ids, names, widths = camera3d._samples(step_m)
    w, h = cam.image_wh
    s = h / 720.0
    uv = cam.project(world)
    inb = (np.isfinite(uv).all(1) & (uv[:, 0] >= 8) & (uv[:, 0] < w - 8)
           & (uv[:, 1] >= 8) & (uv[:, 1] < h - 8))
    nrm = np.zeros_like(uv)
    wpx = np.zeros(len(world))
    if inb.any():
        nrm[inb] = camera3d.line_normals(cam, world[inb], wdir[inb])
        n3 = np.column_stack([-wdir[inb, 1], wdir[inb, 0], np.zeros(inb.sum())])
        half = (widths[ids[inb]] / 2.0)[:, None]
        wpx[inb] = np.linalg.norm(cam.project(world[inb] + n3 * half)
                                  - cam.project(world[inb] - n3 * half), axis=1)
    use = inb & (wpx >= min_width_px_720 * s)
    if not use.any():
        return {"med": float("inf"), "mean": float("inf"), "found": 0.0, "n": 0}
    reach = reach_px_720 * s
    off, found = camera3d.ridge_offsets(grey, uv[use], nrm[use], reach, min_dn)
    d = np.where(found, np.abs(off), reach) / s                    # px @720, censored
    return {"med": float(np.median(d)), "mean": float(d.mean()),
            "found": float(found.mean()), "n": int(use.sum())}


def check_row(grey, cam):
    """paint_check (instrument 1) + ridge_residual (instrument 2) as one dict."""
    c = camera3d.paint_check(grey, cam)
    # c.worst is renamed "too_few_lines" when the lines pass but the court does
    # not; take the worst FRACTION directly so it is always a number.
    worst_frac = min(v[0] for v in c.lines.values()) if c.lines else float("nan")
    r = ridge_residual(grey, cam)
    return {"support": c.support, "ok": bool(c.ok), "worst": c.worst,
            "worst_frac": float(worst_frac), "n_lines": len(c.lines),
            "lines": {k: v[0] for k, v in c.lines.items()},
            "unchecked": list(c.unchecked),
            "ridge_med": r["med"], "ridge_mean": r["mean"],
            "ridge_found": r["found"], "ridge_n": r["n"]}


def self_cost(fcam, meas, lines, cfg=paintfit.FitConfig):
    """Instrument (3): the fit's own final cost on its own measured points.
    `px` is the median |perpendicular residual| in undistorted pixels, `w` the
    median |residual| the optimiser actually minimised (1 / sig_c weighted).
    NOT independent evidence - the fit chose the points and the camera."""
    obs_1, obs_w = [], []
    for L in lines:
        m = meas.get(L.name)
        if m is None or not len(m["pts"]):
            continue
        obs_1.append((L, m["pts"], np.ones(len(m["pts"]))))
        obs_w.append((L, m["pts"], 1.0 / np.maximum(m["sig_c"], cfg.sig_c_floor)))
    if not obs_1:
        return {"px_med": float("inf"), "px_p90": float("inf"), "w_med": float("inf"), "n": 0}
    p = fcam.params()
    args = (True, fcam.cx, fcam.cy, fcam.lam, fcam.wh)
    r1 = np.abs(paintfit._cam_residuals(p, obs_1, *args)[:-4])     # last 4 = in-front penalty
    rw = np.abs(paintfit._cam_residuals(p, obs_w, *args)[:-4])
    return {"px_med": float(np.median(r1)), "px_p90": float(np.percentile(r1, 90)),
            "w_med": float(np.median(rw)), "n": int(len(r1))}


def run_trial(job):
    """Arm K, trial by trial, exactly as tools/court_camera3d_seed.py builds it -
    same SeedSequence, same scene, same keypoint noise, same fitter - plus the
    three G7 instruments on the image the fit saw."""
    trial, seed = job["trial"], job["seed"]
    a = T.ARMS["P"]
    t0 = time.time()
    ss = np.random.SeedSequence([seed, trial])
    r_scene, r_seed, r_noise = [np.random.default_rng(x) for x in ss.spawn(3)]
    contrast = float(r_scene.uniform(*T.CONTRAST_RANGE))
    psf = float(T.PSF_GRID[int(r_scene.integers(len(T.PSF_GRID)))])
    rcam, _, _ = T.truth_camera(a["distortion"], 0.0)

    names, uv = [], []
    for n, p in court.LANDMARKS_3D.items():
        q = rcam.project([p])[0]
        if np.isfinite(q).all() and 0 <= q[0] < T.W and 0 <= q[1] < T.H:
            names.append(n)
            uv.append(q)
    uv = np.array(uv) + r_seed.normal(0.0, T.TAP_SIGMA_PRIMARY, (len(uv), 2))
    bad = r_seed.choice(len(names), N_OUTLIERS, replace=False)
    ang = r_seed.uniform(0, 2 * np.pi, N_OUTLIERS)
    mag = r_seed.uniform(*OUTLIER_PX, N_OUTLIERS)
    uv[bad] += np.column_stack([np.cos(ang), np.sin(ang)]) * mag[:, None]
    kps = {n: tuple(p) for n, p in zip(names, uv)}

    cov = T._coverage_for(a)
    frames = T.noisy_frames(T.clean_image(cov, contrast, psf), a["frames"], r_noise, a["noise"])
    with tempfile.TemporaryDirectory(dir=job.get("tmp")) as td:
        img, kbps = T.codec_mean(frames, td)
    g8 = np.clip(img, 0, 255).astype(np.uint8)
    row = {"trial": trial, "contrast": contrast, "psf": psf, "kbps": kbps,
           "n_kps": len(names), "outliers": [names[i] for i in bad]}
    # the CEILING: the exact rendering camera, on this same image (hard rule 1)
    tcam3d = camera3d.CourtCamera.from_paintfit(rcam, "truth: the rendering camera")
    row["true"] = check_row(g8, tcam3d)
    try:
        s = camera3d.solve_pnp_seed(kps, (T.W, T.H))
        if s is None:
            raise RuntimeError("PnP seed refused")
        row.update({"dropped_cross_ratio": s.dropped_cross_ratio,
                    "outliers_kept": sorted(set(row["outliers"]) & set(s.inliers)),
                    "seed_f": s.camera.f_px, "seed_h": float(s.camera.position_m()[2])})
        seed_pf = s.camera.to_paintfit()
        row["seed"] = check_row(g8, s.camera)
        fcam, meas, lines, sig, kappa = paintfit.r1_fit(img, None, seed_cam=seed_pf)
        per, fb = T.readouts(fcam, meas, lines, rcam, rcam)
        row.update({"ok": True, "lines": per, "sig_est": sig, "kappa": kappa,
                    "f_fit": fcam.f, "lam_fit": fcam.lam, "cam_h": float(fcam.C[2]),
                    "params": fcam.params().tolist(), "seed_params": seed_pf.params().tolist()})
        row["fit"] = check_row(g8, camera3d.CourtCamera.from_paintfit(fcam, "fit"))
        row["self"] = self_cost(fcam, meas, lines)
    except Exception as ex:
        row.update({"ok": False, "error": repr(ex)})
    row["t_total_s"] = round(time.time() - t0, 2)
    return row


# ------------------------------------------------------------- analysis -----
def f_true():
    return (T.W / 2.0) / math.tan(math.radians(T.HFOV_DEG) / 2.0)


def label_wrong(rows):
    ft = f_true()
    return np.array([abs(r["f_fit"] - ft) / ft > WRONG_F_REL for r in rows])


# Each instrument: (name, per-row getter, sign). sign = -1 when a LOW value means
# WRONG (support, worst_frac); +1 when a HIGH value means WRONG (residuals).
INSTRUMENTS = [
    ("paint_check.support",        lambda r: r["fit"]["support"],     -1),
    ("paint_check.worst_line",     lambda r: r["fit"]["worst_frac"],  -1),
    ("ridge_residual.median",      lambda r: r["fit"]["ridge_med"],   +1),
    ("ridge_residual.mean",        lambda r: r["fit"]["ridge_mean"],  +1),
    ("ridge_residual.frac_found",  lambda r: r["fit"]["ridge_found"], -1),
    ("fit_own_cost.px_median",     lambda r: r["self"]["px_med"],     +1),
    ("fit_own_cost.weighted",      lambda r: r["self"]["w_med"],      +1),
]


def _oriented(vals, sign):
    """Orient so that a LARGER score always means MORE LIKELY WRONG."""
    v = np.asarray(vals, float) * sign
    return np.where(np.isfinite(v), v, np.nanmax(v[np.isfinite(v)]) + 1e6 if
                    np.isfinite(v).any() else 0.0)


def _threshold_at_catch(score, wrong, target=0.90):
    """Lowest threshold t (score >= t flags WRONG) catching >= `target` of the
    wrong cameras. None if impossible."""
    w = score[wrong]
    if not len(w):
        return None
    k = int(math.ceil(target * len(w)))
    t = np.sort(w)[::-1][k - 1] if k <= len(w) else None
    return None if t is None else float(t)


def _rates(score, wrong, t):
    flag = score >= t
    catch = float(flag[wrong].mean()) if wrong.any() else float("nan")
    false = float(flag[~wrong].mean()) if (~wrong).any() else float("nan")
    return catch, false


def _split(n, wrong, split_seed):
    """Stratified 50/50 split: each class halved, so both sides hold about the
    same share of wrong cameras."""
    rng = np.random.default_rng(split_seed)
    train = np.zeros(n, bool)
    for cls in (True, False):
        idx = np.flatnonzero(wrong == cls)
        rng.shuffle(idx)
        train[idx[:len(idx) // 2]] = True
    return train


def verdict(catch, false_at_90):
    if not np.isfinite(catch):
        return "NO DATA"
    if catch >= 0.90 and false_at_90 <= 0.02:
        return "SEPARATES"
    if false_at_90 > 0.10:
        return "FAILS"
    return "PARTIAL"


def analyse(rows, split_seed=0, n_perm=1000, perm_seed=0):
    ok = [r for r in rows if r.get("ok")]
    wrong = label_wrong(ok)
    n, nw = len(ok), int(wrong.sum())
    out = {"n": len(rows), "n_ok": n, "n_wrong": nw, "n_right": n - nw,
           "wrong_rule": f"|f_fit - {f_true():.2f}| / f_true > {WRONG_F_REL}",
           "split_seed": split_seed, "instruments": {}}
    train = _split(n, wrong, split_seed)
    qs = (0, 5, 10, 25, 50, 75, 90, 95, 100)
    for name, get, sign in INSTRUMENTS:
        raw = np.array([get(r) for r in ok], float)
        score = _oriented(raw, sign)
        d = {"sign": "low means wrong" if sign < 0 else "high means wrong",
             "wrong": {f"p{q}": float(np.percentile(raw[wrong], q)) for q in qs} if nw else {},
             "right": {f"p{q}": float(np.percentile(raw[~wrong], q)) for q in qs}}
        # overlap: share of right cameras inside the wrong group's min..max range
        if nw:
            lo, hi = raw[wrong].min(), raw[wrong].max()
            d["right_inside_wrong_range"] = float(((raw[~wrong] >= lo)
                                                   & (raw[~wrong] <= hi)).mean())
        if nw < 2 or (n - nw) < 2:          # nothing to separate in this run
            d["note"] = "too few of one class to threshold"
            out["instruments"][name] = d
            continue
        # in-sample trade-off curve at several catch targets
        curve = {}
        for tgt in (0.80, 0.90, 0.95, 1.00):
            t = _threshold_at_catch(score, wrong, tgt)
            if t is not None:
                c, f = _rates(score, wrong, t)
                curve[f"catch{int(tgt * 100)}"] = {"threshold_oriented": t,
                                                   "threshold_raw": t * sign,
                                                   "catch": c, "false_flag": f}
        d["in_sample"] = curve
        # pre-registered held-out evaluation
        t = _threshold_at_catch(score[train], wrong[train], 0.90)
        if t is not None:
            c, f = _rates(score[~train], wrong[~train], t)
            # the cost of catching 90% ON the held-out half, for the FAILS half
            # of the bar ("catching 90% costs > 10% false rejection")
            t2 = _threshold_at_catch(score[~train], wrong[~train], 0.90)
            f90 = _rates(score[~train], wrong[~train], t2)[1] if t2 is not None else 1.0
            d["held_out"] = {"threshold_oriented": t, "threshold_raw": t * sign,
                             "catch": c, "false_flag": f,
                             "false_flag_at_catch90_in_held_out": f90,
                             "n_wrong_held_out": int(wrong[~train].sum()),
                             "n_right_held_out": int((~wrong[~train]).sum()),
                             "verdict": verdict(c, f) if (c >= 0.90 and f <= 0.02)
                                        else ("FAILS" if f90 > 0.10 else "PARTIAL")}
        # null control: permute the labels, re-run the whole procedure
        rng = np.random.default_rng(perm_seed)
        cs, fs = [], []
        for _ in range(n_perm):
            pw = rng.permutation(wrong)
            tr = _split(n, pw, split_seed)
            tt = _threshold_at_catch(score[tr], pw[tr], 0.90)
            if tt is None:
                continue
            c2, f2 = _rates(score[~tr], pw[~tr], tt)
            cs.append(c2)
            fs.append(f2)
        d["null_permuted"] = ({"n_perm": 0} if not cs else
                              {"n_perm": len(cs), "catch_mean": float(np.mean(cs)),
                               "catch_p95": float(np.percentile(cs, 95)),
                               "false_flag_mean": float(np.mean(fs)),
                               "separates_rate": float(np.mean([(c >= 0.90) and (f <= 0.02)
                                                                for c, f in zip(cs, fs)]))})
        out["instruments"][name] = d
    # the ceiling: the true camera on the same images
    out["ceiling_true_camera"] = {
        k: {f"p{q}": float(np.percentile([r["true"][k] for r in ok], q)) for q in qs}
        for k in ("support", "worst_frac", "ridge_med", "ridge_mean", "ridge_found")}
    out["ceiling_true_camera"]["ok_rate"] = float(np.mean([r["true"]["ok"] for r in ok]))
    out["ceiling_true_camera"]["unchecked_lines"] = sorted(
        {x for r in ok for x in r["true"]["unchecked"]})
    # what the shipped paint_check ok flag does on its own
    okflag = np.array([r["fit"]["ok"] for r in ok])
    out["shipped_paint_check_ok_flag"] = {
        "catch": float((~okflag[wrong]).mean()) if nw else float("nan"),
        "false_flag": float((~okflag[~wrong]).mean()),
        "note": "catch = wrong cameras the shipped ok flag calls NOT ok"}
    # how wrong is wrong: worst line error on each group
    def worst_line(r):
        return max(max(v["M"], v["L"]) for v in r["lines"].values())
    wl = np.array([worst_line(r) for r in ok])
    out["worst_line_m"] = {"wrong_p50": float(np.median(wl[wrong])) if nw else None,
                           "right_p50": float(np.median(wl[~wrong])),
                           "right_p90": float(np.percentile(wl[~wrong], 90))}
    return out


def main():
    from concurrent.futures import ProcessPoolExecutor
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--split-seed", type=int, default=0)
    ap.add_argument("--perm-seed", type=int, default=0)
    ap.add_argument("--n-perm", type=int, default=1000)
    ap.add_argument("--out", default=None)
    ap.add_argument("--analyse", default=None, help="re-analyse an existing rows file")
    args = ap.parse_args()

    if args.analyse:
        d = json.loads(Path(args.analyse).read_text(encoding="utf-8"))
        a = analyse(d["rows"], args.split_seed, args.n_perm, args.perm_seed)
        print(json.dumps(a, indent=1))
        return

    T._coverage_for(T.ARMS["P"])
    tmp = OUT_DIR / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    jobs = [{"trial": i, "seed": args.seed, "tmp": str(tmp)} for i in range(args.n)]
    t0 = time.time()
    with ProcessPoolExecutor(args.workers) as ex:
        rows = []
        for k, r in enumerate(ex.map(run_trial, jobs, chunksize=1)):
            rows.append(r)
            if (k + 1) % 25 == 0:
                print(f"  {k + 1}/{args.n}  {time.time() - t0:.0f}s", flush=True)
    a = analyse(rows, args.split_seed, args.n_perm, args.perm_seed)
    a["wall_s"] = time.time() - t0
    stamp = {"tool": "tools/court_cost_separation.py", "section": "G7",
             "commit": T.git_sha(), "dirty": T.git_dirty(), "n": args.n, "seed": args.seed,
             "workers": args.workers, "scene": "CP1 arm P", "arm": "K (plain paintfit.r1_fit)",
             "seed_model": f"{len(court.LANDMARKS_3D)} 3D keypoints in frame, sigma "
                           f"{T.TAP_SIGMA_PRIMARY} px + {N_OUTLIERS} outliers {OUTLIER_PX} px",
             "principal_point": "image centre",
             "fitter": paintfit.FitConfig.as_dict(), "codec": T.X265,
             "ridge_residual": {"reach_px_720": RIDGE_REACH_PX_720, "min_dn": RIDGE_MIN_DN,
                                "min_width_px_720": RIDGE_MIN_WIDTH_PX_720,
                                "step_m": RIDGE_STEP_M,
                                "censoring": "no ridge found scores the full reach"},
             "paint_check": "camera3d.paint_check shipped defaults",
             "wrong_rule": a["wrong_rule"],
             "measured_against": "the exact rendering camera (court_fit_cp1.truth_camera); "
                                 "the wrong/right label is its focal length"}
    out = Path(args.out or OUT_DIR / f"G7_seed{args.seed}_n{args.n}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(T._jsonable({"stamp": stamp, "analysis": a, "rows": rows}), indent=1),
                   encoding="utf-8")
    print(f"n_ok={a['n_ok']}  wrong={a['n_wrong']}  right={a['n_right']}")
    print(f"{'instrument':<28}{'held-out catch':>15}{'false flag':>12}  verdict")
    for k, v in a["instruments"].items():
        h = v.get("held_out")
        if h:
            print(f"{k:<28}{h['catch']:15.3f}{h['false_flag']:12.3f}  {h['verdict']}")
    print("ceiling (true camera):", {k: round(v["p50"], 4) for k, v in
                                     a["ceiling_true_camera"].items() if isinstance(v, dict)})
    print("wrote", out)


if __name__ == "__main__":
    main()
