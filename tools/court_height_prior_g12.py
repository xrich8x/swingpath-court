"""court_height_prior_g12.py - G12: do height-prior seeds turn CP1's wrong-camera
basins into locked right cameras?

The founder's Phase 2 (docs/DECISIONS_PENDING.md item 3). G1: plain `r1_fit` from
the keypoint PnP seed lands in a WRONG camera on 8.75% of CP1 arm-K trials, in
discrete dolly-zoom basins predicted by the seed's height error. G7: the shipped
`paint_check` catches every one, so today they are honest failures to lock. This
runs THREE setups on the SAME image and the SAME noisy keypoints, paired:

  plain     paintfit.r1_fit from the PnP seed (G1's arm K)
  checked   camera3d.fit_camera_checked (shipped: restarts when the check fails)
  anchored  camera3d.fit_camera_anchored (fits from 1.5 / 2.5 / 3.5 m; the
            independent paint_check picks the winner, never the fit's cost)

Truth is CP1's exact rendering camera (court_fit_cp1.truth_camera). A camera is
WRONG when its fitted focal length is > 1% off (G1's rule, recomputed here);
per-line placement is C1's M readout (ground error through the fitted camera,
court_fit_cp1.readouts), against that rendering camera.

    python tools/court_height_prior_g12.py --n 200 --seed 1100
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import court_cost_separation as CS                                 # noqa: E402
import court_fit_cp1 as T                                          # noqa: E402
from swingvision import camera3d, court, paintfit                  # noqa: E402

OUT_DIR = REPO / "data" / "output" / "court_height_prior_g12"
ARMS = ("plain", "checked", "anchored")


def _lines_m(pfcam, meas, lines, rcam):
    per, _ = T.readouts(pfcam, meas, lines, rcam, rcam)
    return {k: float(v["M"]) for k, v in per.items()}


def run_trial(job):
    """CP1 arm K's trial, built exactly as court_cost_separation.run_trial builds
    it (same SeedSequence layout, scene, keypoint noise, outliers, codec)."""
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
    bad = r_seed.choice(len(names), CS.N_OUTLIERS, replace=False)
    ang = r_seed.uniform(0, 2 * np.pi, CS.N_OUTLIERS)
    mag = r_seed.uniform(*CS.OUTLIER_PX, CS.N_OUTLIERS)
    uv[bad] += np.column_stack([np.cos(ang), np.sin(ang)]) * mag[:, None]
    kps = {n: tuple(p) for n, p in zip(names, uv)}
    cov = T._coverage_for(a)
    frames = T.noisy_frames(T.clean_image(cov, contrast, psf), a["frames"], r_noise, a["noise"])
    with tempfile.TemporaryDirectory(dir=job.get("tmp")) as td:
        img, kbps = T.codec_mean(frames, td)
    g8 = np.clip(img, 0, 255).astype(np.uint8)
    lines = paintfit.paint_lines()
    ft = CS.f_true()
    row = {"trial": trial, "contrast": contrast, "psf": psf, "kbps": kbps}
    try:
        s = camera3d.solve_pnp_seed(kps, (T.W, T.H))
        if s is None:
            raise RuntimeError("PnP seed refused")
        row["seed_f"], row["seed_h"] = s.camera.f_px, float(s.camera.position_m()[2])
    except Exception as ex:
        row["error"] = repr(ex)
        return row
    for arm in ARMS:
        ta = time.time()
        try:
            if arm == "plain":
                fcam, meas, _l, _s, _k = paintfit.r1_fit(img, None, seed_cam=s.camera.to_paintfit())
                cam = camera3d.CourtCamera.from_paintfit(fcam, "plain")
                extra = {}
            else:
                fn = (camera3d.fit_camera_checked if arm == "checked"
                      else camera3d.fit_camera_anchored)
                res = fn(img, s.camera)
                cam, meas, extra = res.camera, res.meas, dict(res.camera.extra)
                fcam = cam.to_paintfit()
            chk = camera3d.paint_check(g8, cam)
            row[arm] = {"ok": bool(chk.ok), "worst": chk.worst,
                        "f_px": float(cam.f_px), "height_m": float(cam.position_m()[2]),
                        "wrong": abs(cam.f_px - ft) / ft > CS.WRONG_F_REL,
                        "lines_m": _lines_m(fcam, meas, lines, rcam),
                        "starts": extra.get("starts"),
                        "height_prior_m": extra.get("height_prior_m"),
                        "anchors": extra.get("anchors"),
                        "t_s": round(time.time() - ta, 2)}
        except Exception as ex:
            row[arm] = {"error": repr(ex), "ok": False, "wrong": None}
    row["t_total_s"] = round(time.time() - t0, 2)
    return row


def analyse(rows):
    good = [r for r in rows if all(arm in r and "error" not in r[arm] for arm in ARMS)]
    out = {"n_rows": len(rows), "n_scored": len(good),
           "n_errored": len(rows) - len(good), "arms": {}}
    for arm in ARMS:
        ok = np.array([r[arm]["ok"] for r in good])
        wrong = np.array([bool(r[arm]["wrong"]) for r in good])
        right_locked = [r for r in good if r[arm]["ok"] and not r[arm]["wrong"]]
        lines = {}
        if right_locked:
            for k in right_locked[0][arm]["lines_m"]:
                v = np.array([r[arm]["lines_m"][k] for r in right_locked])
                lines[k] = {"p50": float(np.percentile(v, 50)), "p90": float(np.percentile(v, 90))}
        out["arms"][arm] = {
            "wrong_rate": float(wrong.mean()), "n_wrong": int(wrong.sum()),
            "locked_rate": float(ok.mean()),
            "locked_and_wrong": int((ok & wrong).sum()),
            "locked_and_right_rate": float((ok & ~wrong).mean()),
            "n_locked_and_right": int((ok & ~wrong).sum()),
            "worst_line_p90_locked_right_m": max((v["p90"] for v in lines.values()),
                                                 default=math.inf),
            "lines_locked_right": lines,
            "t_s_p50": float(np.median([r[arm]["t_s"] for r in good]))}
    A, P, C = out["arms"]["anchored"], out["arms"]["plain"], out["arms"]["checked"]
    out["bars"] = {
        "K1 anchored: zero locked-and-wrong": A["locked_and_wrong"] == 0,
        "K2 anchored wrong-camera rate < plain's AND <= 2%": (A["wrong_rate"] < P["wrong_rate"]
                                                              and A["wrong_rate"] <= 0.02),
        "K3 anchored locked-and-right >= checked's": (A["n_locked_and_right"]
                                                      >= C["n_locked_and_right"]),
        "K4 anchored every line p90 <= 5 cm on its locked right cameras":
            A["worst_line_p90_locked_right_m"] <= T.BAR_M,
    }
    out["verdict"] = "PASS" if all(out["bars"].values()) else "FAIL"
    out["failed"] = [k for k, v in out["bars"].items() if not v]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1100)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--out", default=None)
    ap.add_argument("--analyse", default=None)
    a = ap.parse_args()
    if a.analyse:
        d = json.loads(Path(a.analyse).read_text(encoding="utf-8"))
        print(json.dumps(analyse(d["rows"]), indent=1))
        return
    T._coverage_for(T.ARMS["P"])
    tmp = OUT_DIR / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    jobs = [{"trial": i, "seed": a.seed, "tmp": str(tmp)} for i in range(a.n)]
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for k, r in enumerate(ex.map(run_trial, jobs, chunksize=1)):
            rows.append(r)
            if (k + 1) % 20 == 0:
                print(f"  {k + 1}/{a.n}  {time.time() - t0:.0f}s", flush=True)
    res = {"stamp": {"tool": "tools/court_height_prior_g12.py", "gate": "G12",
                     "commit": T.git_sha(), "dirty": T.git_dirty(), "n": a.n, "seed": a.seed,
                     "scene": "CP1 arm P", "seed_model": "court_cost_separation arm K",
                     "height_priors_m": list(camera3d.HEIGHT_PRIORS_M),
                     "restarts_checked": [list(r) for r in camera3d.RESTARTS],
                     "wrong_rule": f"|f - {CS.f_true():.2f}| / f_true > {CS.WRONG_F_REL}",
                     "placement": "C1 M readout (ground error through the fitted camera)",
                     "measured_against": "CP1's exact rendering camera",
                     "wall_s": round(time.time() - t0, 1)},
           "analysis": analyse(rows), "rows": rows}
    out = Path(a.out or OUT_DIR / f"G12_seed{a.seed}_n{a.n}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(T._jsonable(res), indent=1), encoding="utf-8")
    an = res["analysis"]
    for arm, v in an["arms"].items():
        print(f"{arm:9s} wrong {v['n_wrong']:3d} ({v['wrong_rate']:.3f})  locked {v['locked_rate']:.3f}  "
              f"locked&wrong {v['locked_and_wrong']}  locked&right {v['n_locked_and_right']}  "
              f"worst p90 {v['worst_line_p90_locked_right_m'] * 100:.2f} cm  t {v['t_s_p50']:.0f}s")
    for k, v in an["bars"].items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
    print("VERDICT", an["verdict"], "wrote", out)


if __name__ == "__main__":
    main()
