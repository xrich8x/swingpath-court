"""court_camera3d_seed.py - does the 3D court still place every line when its first
guess comes from KEYPOINTS through a PnP solve instead of four corners?

Arm K:  CP1 arm P's scene (Brown lens, fence/truss clutter, noise, 30-frame mean,
        real libx265) - but the seed is 21 named 3D keypoints (court.LANDMARKS_3D,
        the ones in frame) with detector-grade noise (sigma 14.78 px per axis, CP1's
        seed noise) plus TWO gross outliers (100-300 px), through
        camera3d.solve_pnp_seed (no focal given), then camera3d.fit_camera_on_paint.
        The principal point is the image centre (CP1 passed the true cx; qa's
        latent-leak finding).
Arm K0: the same seeds, scored WITHOUT the paint fit - the keypoint camera alone.
Arm KC (--checked): arm K with camera3d.fit_camera_checked - the fit is checked
        ON THE PAINT (per line) and re-started from dolly-zoom seeds if it fails.

Measured against exact projected court geometry from CP1's known synthetic camera,
with CP1's own readouts (M: fitted model; L: measured line). K0 has only M.
The gate is pre-registered in docs/evidence/court-camera3d.md.

    cd backend && .venv/Scripts/python.exe ../tools/court_camera3d_seed.py --n 400 --seed 0
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

OUT_DIR = REPO / "data" / "output" / "court_camera3d_seed"
N_OUTLIERS = 2
OUTLIER_PX = (100.0, 300.0)


def run_trial(job):
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
    row = {"trial": trial, "contrast": contrast, "psf": psf, "kbps": kbps,
           "n_kps": len(names), "outliers": [names[i] for i in bad]}
    try:
        s = camera3d.solve_pnp_seed(kps, (T.W, T.H))
        if s is None:
            raise RuntimeError("PnP seed refused")
        row.update({"dropped_cross_ratio": s.dropped_cross_ratio,
                    "outliers_kept": sorted(set(row["outliers"]) & set(s.inliers)),
                    "seed_f": s.camera.f_px, "seed_h": float(s.camera.position_m()[2])})
        seed_pf = s.camera.to_paintfit()
        k0, _ = T.readouts(seed_pf, {}, T.paint_lines(), rcam, rcam)
        row["K0"] = {k: v["M"] for k, v in k0.items()}
        g8 = np.clip(img, 0, 255).astype(np.uint8)
        if job.get("checked"):
            res = camera3d.fit_camera_checked(img, s.camera)
            fcam = res.camera.to_paintfit()
            meas, lines = res.meas, paintfit.paint_lines()
            sig, kappa = res.sigma_px, res.kappa
            row.update({"check": res.camera.extra["paint_check"],
                        "starts": res.camera.extra["starts"]})
        else:
            fcam, meas, lines, sig, kappa = paintfit.r1_fit(img, None, seed_cam=seed_pf)
        per, fb = T.readouts(fcam, meas, lines, rcam, rcam)
        row.update({"ok": True, "lines": per, "far_bl": fb, "sig_est": sig, "kappa": kappa,
                    "f_fit": fcam.f, "lam_fit": fcam.lam, "cam_h": float(fcam.C[2]),
                    "params": fcam.params().tolist(), "seed_params": seed_pf.params().tolist(),
                    "support": camera3d.paint_support(
                        g8, camera3d.CourtCamera.from_paintfit(fcam, "fit"))})
    except Exception as ex:                       # a failed trial is a FAILURE row
        row.update({"ok": False, "error": repr(ex)})
    row["t_total_s"] = round(time.time() - t0, 2)
    return row


def summarise(rows):
    names = [n for n, *_ in T.C1.lines()]

    def q(v, p):
        return float(np.percentile(np.asarray(v, float), p))

    def verdict(worst):
        return "PASS" if worst <= T.BAR_M else ("KILL" if worst > T.KILL_M else "INDETERMINATE")
    K, K0 = {}, {}
    for n in names:
        M = [r["lines"][n]["M"] if r["ok"] else math.inf for r in rows]
        L = [r["lines"][n]["L"] if r["ok"] else math.inf for r in rows]
        S = [r["K0"][n] if "K0" in r else math.inf for r in rows]
        K[n] = {"M_p50": q(M, 50), "M_p90": q(M, 90), "L_p50": q(L, 50), "L_p90": q(L, 90),
                "max_over_5cm": int(sum(max(m, l) > T.BAR_M for m, l in zip(M, L)))}
        K[n]["verdict"] = verdict(max(K[n]["M_p90"], K[n]["L_p90"]))
        K0[n] = {"M_p50": q(S, 50), "M_p90": q(S, 90)}
        K0[n]["verdict"] = verdict(K0[n]["M_p90"])
    ok = [r for r in rows if r["ok"]]
    f_true = (T.W / 2.0) / math.tan(math.radians(T.HFOV_DEG) / 2.0)
    return {
        "n": len(rows), "failures": len(rows) - len(ok),
        "errors": sorted({r["error"] for r in rows if not r["ok"]}),
        "K": K, "K_pass_all": all(v["verdict"] == "PASS" for v in K.values()),
        "K0": K0,
        "outliers_kept_by_seed": int(sum(bool(r.get("outliers_kept")) for r in rows)),
        "cross_ratio_dropped_any": int(sum(bool(r.get("dropped_cross_ratio")) for r in rows)),
        "seed_f_err_pct_p90": q([abs(r["seed_f"] - f_true) / f_true * 100 for r in rows
                                 if "seed_f" in r], 90),
        "f_err_pct_p90": q([abs(r["f_fit"] - f_true) / f_true * 100 for r in ok], 90) if ok else None,
        "cam_h_abs_err_p90": q([abs(r["cam_h"] - T.MOUNT_M) for r in ok], 90) if ok else None,
        "wrong_camera": int(sum(abs(r["f_fit"] - f_true) / f_true > 0.01 for r in ok)),
        "check_failed": int(sum(str(r.get("check", "")).startswith("FAIL") for r in ok)),
        "wrong_but_check_passed": int(sum(abs(r["f_fit"] - f_true) / f_true > 0.01
                                          and r.get("check") == "pass" for r in ok)),
        "restarted": int(sum(r.get("starts", 1) > 1 for r in ok)),
    }


def main():
    from concurrent.futures import ProcessPoolExecutor
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--out", default=None)
    ap.add_argument("--checked", action="store_true", help="arm KC")
    args = ap.parse_args()
    T._coverage_for(T.ARMS["P"])
    tmp = OUT_DIR / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    jobs = [{"trial": i, "seed": args.seed, "tmp": str(tmp), "checked": args.checked}
            for i in range(args.n)]
    t0 = time.time()
    with ProcessPoolExecutor(args.workers) as ex:
        rows = []
        for k, r in enumerate(ex.map(run_trial, jobs, chunksize=1)):
            rows.append(r)
            if (k + 1) % 25 == 0:
                print(f"  {k + 1}/{args.n}  {time.time() - t0:.0f}s", flush=True)
    s = summarise(rows)
    s["wall_s"] = time.time() - t0
    stamp = {"tool": "tools/court_camera3d_seed.py", "commit": T.git_sha(), "n": args.n,
             "seed": args.seed, "workers": args.workers, "scene": "CP1 arm P",
             "arm": "KC" if args.checked else "K",
             "seed_model": f"{len(court.LANDMARKS_3D)} 3D keypoints in frame, sigma "
                           f"{T.TAP_SIGMA_PRIMARY} px + {N_OUTLIERS} outliers {OUTLIER_PX} px",
             "principal_point": "image centre", "fitter": paintfit.FitConfig.as_dict(),
             "codec": T.X265,
             "measured_against": "exact projected court geometry from CP1's synthetic camera"}
    arm = "KC" if args.checked else "K"
    out = Path(args.out or OUT_DIR / f"{arm}_seed{args.seed}_n{args.n}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(T._jsonable({"stamp": stamp, "summary": s, "rows": rows}), indent=1),
                   encoding="utf-8")
    print(f"n={s['n']} failures={s['failures']} {s['errors']}")
    print(f"{'line':<26}{'K M p90':>9}{'K L p90':>9}{'>5cm':>6}  verdict   {'K0 p90':>9}")
    for n, v in s["K"].items():
        print(f"{n:<26}{v['M_p90']:9.4f}{v['L_p90']:9.4f}{v['max_over_5cm']:6d}  "
              f"{v['verdict']:<9} {s['K0'][n]['M_p90']:9.3f} {s['K0'][n]['verdict']}")
    print({k: s[k] for k in ("wrong_camera", "check_failed", "wrong_but_check_passed",
                             "restarted", "outliers_kept_by_seed", "cross_ratio_dropped_any",
                             "seed_f_err_pct_p90", "f_err_pct_p90", "cam_h_abs_err_p90")})
    print("wrote", out)


if __name__ == "__main__":
    main()
