"""court_track_sim.py - does the court stay placed while the phone sways?

WHY THIS EXISTS
---------------
Founder ruling 2026-09-17: live court tracking continues when the phone moves.
`calibration.court_lock_step` (+ CourtWatchdog) is the only tracker that has
existed here and its precision was never measured (lead journal, queue item 3).
`camtrack.CameraTracker` is the 3D replacement. This renders a court seen by a
fence-mounted camera that sways and takes one knock, runs both trackers, and
scores where each puts every line.

WHAT IT MEASURES, AND AGAINST WHAT
----------------------------------
Measured against the EXACT synthetic camera that rendered each frame: for each
of C1's 14 line halves, 11 points on the true line are projected with the true
camera and back-projected to the ground with the tracked estimate; the error is
the worst perpendicular ground distance (metres), as in C1 and CP1. Also: the
largest frame-to-frame "grid jump" - how far the tracked far baseline moved in
the image beyond how far the true one moved (px).

The pre-registered gates are in docs/evidence/court-camera3d.md (G3, and G6 for
the checked tracker), each committed before its first scored run. From G6 on,
setup uses camera3d.fit_camera_checked and every frame records whether the
tracker claimed a lock; `locked_wrong` counts frames that claim a lock while
some line is more than 10 cm out - the silent failure G3 exposed.

THE RENDERER IS SIMPLER THAN CP1's: 5 cm paint on a flat surface, supersampled
2x2, Gaussian blur, sensor noise, a far fence with posts as clutter; no lens
distortion (the baseline tracker has no lens model, and this measures tracking,
not lens fitting); no codec. It is fast enough to render a moving camera.

    cd backend && .venv/Scripts/python.exe ../tools/court_track_sim.py --seeds 0 1 2
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

import court_map_ceiling as C1                                     # noqa: E402
from swingvision import calibration, camera3d, camtrack, court, paintfit  # noqa: E402

W, H = 1920, 1080
FPS = 30.0
MOUNT_M, SETBACK_M, HFOV_DEG = 3.0, 6.0, 100.0
SURFACE_DN, SKY_DN, FENCE_DN, POST_DN = 95.0, 150.0, 45.0, 30.0
FENCE_Y = court.Y_FAR_BASELINE + 6.40
KNOCK_S = 2.0
KNOCK_WINDOW = 6          # frames from the knock excluded from the steady grid-jump figure
# Supersampling. 2 is what every tracking number before G8 was measured at, and it
# is kept as the default so none of them move. It ALIASES sub-pixel paint: the far
# baseline's 0.19 px of paint is hit by almost no sub-sample, so its stacked normal
# profile reads 0.49 DN at an offset of +3.96 px (noiseless, true camera) against
# 7.9 DN at -0.133 px at ss=16 - the line is effectively absent from the image, and
# far_service is aliased the other way (21.5 DN against 7.9). The OFFSET converges
# from ss=4 (-0.135 / -0.130 / -0.133 at ss 4 / 8 / 16); the amplitude never does,
# because a near-horizontal line has a near-constant sub-pixel phase that stacking
# cannot average. G8 scores the far-line instrument at ss=4. Cost per 1080p frame:
# 0.73 / 2.70 / 10.62 s at ss 2 / 4 / 8.
SS_DEFAULT = 2
# The PSF order. False - blur AFTER binning - is what every pre-G8 tracking number
# was measured at and is kept as the default so none of them move. It cannot place
# a sub-pixel line: binning first collapses a line thinner than a pixel onto that
# pixel's centre. True is CP1's order and is what G8 scores at.
# False is what every pre-G8 tracking number was measured at, and it is kept as the
# default so none of them move. It CANNOT place paint thinner than a pixel, for two
# independent reasons, both measured on the true camera with no noise:
#   * the sub-samples are a fixed grid, so a 0.13-0.19 px band is hit or missed by
#     PHASE - far_service read 21.5 DN and far_baseline 0.49 DN at ss=2 where both
#     should read ~7.9;
#   * the PSF is applied AFTER binning, so a line that lands inside one pixel row is
#     quantised to that row's centre - the far baseline read 0.5 px off at 1280x720,
#     ss=8, and no amount of supersampling removes it.
# True switches to CP1's renderer order (docs/evidence/court-fit-cp1.md s7): JITTERED
# stratified sub-samples, PSF applied at sub-sample resolution, then binned. That is
# what G8 scores the far-line instrument at, and it is a DIFFERENT SCENE: numbers
# from it are not comparable with G3 or with the 100-102 / 200-202 tracking runs.
SUBPIXEL_DEFAULT = False
OUT = REPO / "data" / "output" / "court_track_sim"


# ------------------------------------------------------------ rendering ----
def _paint_rects():
    rects = [L.rect() for L in paintfit.paint_lines()]
    rects += [(x0, x1, y0, y1) for (x0, x1, y0, y1) in paintfit.centre_marks()]
    return np.array(rects, float)


RECTS = _paint_rects()


def camera(yaw, pitch, roll, dx=0.0, dy=0.0, dz=0.0, wh=(W, H), hfov=HFOV_DEG):
    f = (wh[0] / 2.0) / math.tan(math.radians(hfov) / 2.0)
    pf = paintfit.Camera((court.X_CENTER + dx, -SETBACK_M + dy, MOUNT_M + dz), yaw, pitch, roll,
                         f, wh[0] / 2.0, wh[1] / 2.0, wh=wh)
    return camera3d.CourtCamera.from_paintfit(pf, "synthetic truth")


def base_pitch(wh=(W, H)):
    """Pitch that centres the court vertically (as C1 frames it)."""
    from court_camera import frame_the_court
    return math.radians(frame_the_court(MOUNT_M, SETBACK_M, HFOV_DEG, *wh)[1])


def render(cam: camera3d.CourtCamera, rng, contrast=110.0, psf=0.9, noise=True, ss=SS_DEFAULT,
           subpixel=SUBPIXEL_DEFAULT):
    """Grey float image of the court, the far fence and its posts.

    `subpixel` switches to CP1's render order - jittered stratified sub-samples
    and the PSF applied BEFORE binning - which is what it takes to place paint
    thinner than a pixel at all. See SUBPIXEL_DEFAULT for the measurements.
    False keeps every pre-G8 tracking number exactly where it was."""
    from scipy import ndimage
    w, h = cam.image_wh
    pf = cam.to_paintfit()
    off = (np.arange(ss) + 0.5) / ss - 0.5
    ys, xs = np.mgrid[0:h, 0:w]
    acc = np.zeros((h * ss, w * ss), np.float32) if subpixel else np.zeros((h, w))
    for iy in range(ss):
        for ix in range(ss):
            if subpixel:    # jittered inside the stratum: coverage is then unbiased
                ox = (ix + rng.random(h * w)) / ss - 0.5
                oy = (iy + rng.random(h * w)) / ss - 0.5
            else:
                ox, oy = off[ix], off[iy]
            uv = np.column_stack([xs.ravel() + ox, ys.ravel() + oy])   # pixel centres on integers
            d = pf.rays(uv)
            C = pf.C
            val = np.full(len(d), SKY_DN)
            with np.errstate(divide="ignore", invalid="ignore"):
                tg = np.where(d[:, 2] < 0, -C[2] / d[:, 2], np.inf)
                tf = np.where(d[:, 1] > 0, (FENCE_Y - C[1]) / d[:, 1], np.inf)
            hit_g = np.isfinite(tg) & (tg < tf)
            gx = C[0] + tg * d[:, 0]
            gy = C[1] + tg * d[:, 1]
            val[hit_g] = SURFACE_DN
            paint = np.zeros(len(d), bool)
            for x0, x1, y0, y1 in RECTS:
                paint |= hit_g & (gx >= x0) & (gx <= x1) & (gy >= y0) & (gy <= y1)
            val[paint] = SURFACE_DN + contrast
            hit_f = np.isfinite(tf) & ~hit_g
            fz = C[2] + tf * d[:, 2]
            fx = C[0] + tf * d[:, 0]
            on_f = hit_f & (fz >= 0) & (fz <= 4.0)
            val[on_f] = FENCE_DN
            post = on_f & (np.abs(((fx + 1.5) % 3.0) - 1.5) < 0.04)
            val[post] = POST_DN
            if subpixel:
                acc[iy::ss, ix::ss] = val.reshape(h, w)
            else:
                acc += val.reshape(h, w)
    if subpixel:
        img = ndimage.gaussian_filter(acc, psf * ss).reshape(h, ss, w, ss).mean((1, 3))
        img = img.astype(float)
    else:
        img = ndimage.gaussian_filter(acc / (ss * ss), psf)
    if noise:
        img = img + rng.normal(0.0, 1.0, img.shape) * np.sqrt(3.0 / 128.0 * img + 1.0)
    return np.clip(img, 0, 255)


# --------------------------------------------------------------- motion ----
def sway_path(n, rng, knock_s=KNOCK_S, knock_scale=1.0):
    """Per-frame (yaw, pitch, roll, dx, dy, dz) offsets: a fence swaying in wind
    (sinusoids plus a slow random walk, ~0.3 deg and ~1 cm) and one knock at
    `knock_s` (+1.5 deg pitch, +1 deg yaw, held; x `knock_scale`)."""
    t = np.arange(n) / FPS
    out = np.zeros((n, 6))
    amp = np.radians([0.3, 0.3, 0.15])
    for k in range(3):
        f1, f2 = rng.uniform(0.4, 1.2), rng.uniform(1.5, 3.0)
        p1, p2 = rng.uniform(0, 2 * np.pi, 2)
        out[:, k] = amp[k] * (0.7 * np.sin(2 * np.pi * f1 * t + p1)
                              + 0.3 * np.sin(2 * np.pi * f2 * t + p2))
        out[:, k] += np.cumsum(rng.normal(0, np.radians(0.01), n))
    for k in range(3, 6):
        out[:, k] = 0.01 * np.sin(2 * np.pi * rng.uniform(0.5, 2.0) * t + rng.uniform(0, 6.3))
    knock = t >= knock_s
    out[knock, 0] += np.radians(1.0 * knock_scale)
    out[knock, 1] += np.radians(1.5 * knock_scale)
    return out


# -------------------------------------------------------------- scoring ----
LINES = C1.lines()


def line_errors(true_cam, ground_fn):
    """{line half: worst perpendicular ground error (m)} for an estimate given as
    `ground_fn(uv) -> (N, 2)`."""
    out = {}
    for name, a, b, nrm in LINES:
        t = np.linspace(0, 1, 11)[:, None]
        xy = (1 - t) * np.array(a) + t * np.array(b)
        uv = true_cam.project(np.column_stack([xy, np.zeros(11)]))
        g = ground_fn(uv)
        e = np.abs((g - xy) @ np.array(nrm, float))
        out[name] = float(np.max(e)) if np.all(np.isfinite(e)) else math.inf
    return out


def far_baseline_px(ground_to_img):
    xs = np.linspace(0.5, court.DOUBLES_WIDTH - 0.5, 20)
    return ground_to_img(np.column_stack([xs, np.full(20, court.Y_FAR_BASELINE)]))


def summarise(runs):
    """Pooled over runs; each run is {"frames": [per-line errors], "jumps":
    [(frame index, excess px)], "knock": frame index}."""
    names = [n for n, *_ in LINES]
    frames = [f for r in runs for f in r["frames"]]
    lines = {}
    for n in names:
        v = np.array([f[n] for f in frames], float)
        lines[n] = {"p50": float(np.percentile(v, 50)), "p90": float(np.percentile(v, 90)),
                    "max": float(v.max())}
    worst = max(v["p90"] for v in lines.values())
    verdict = ("PASS" if worst <= C1.BAR_M else "KILL" if worst > C1.KILL_M
               else "INDETERMINATE")
    steady = [j for r in runs for i, j in r["jumps"]
              if not r["knock"] <= i < r["knock"] + KNOCK_WINDOW]
    recovery = []
    for r in runs:
        after = [i for i in range(r["knock"], len(r["frames"]))
                 if max(r["frames"][i].values()) <= C1.BAR_M]
        recovery.append(after[0] - r["knock"] if after else None)
    out = {"lines": lines, "worst_p90_m": worst, "verdict": verdict,
           "max_steady_jump_px": float(np.max(steady)) if steady else 0.0,
           "max_jump_px": float(np.max([j for r in runs for _, j in r["jumps"]])),
           "knock_recovery_frames": recovery}
    if all(r.get("locked") is not None for r in runs):
        lk = [(l, max(f.values())) for r in runs for l, f in zip(r["locked"], r["frames"])]
        out["locked_frames"] = int(sum(l for l, _ in lk))
        out["locked_wrong"] = int(sum(l and e > C1.KILL_M for l, e in lk))
        out["unlocked_frames"] = int(sum(not l for l, _ in lk))
        lw = [e for l, e in lk if l]
        out["locked_worst_p90_m"] = float(np.percentile(lw, 90)) if lw else math.inf
    return out


# ----------------------------------------------------------------- arms ----
def run(seed=0, n=120, seed_sigma=14.78, verbose=True, knock_scale=1.0, ss=SS_DEFAULT,
        subpixel=SUBPIXEL_DEFAULT, far_lines=camtrack.TrackConfig.far_lines):
    r_path, r_img, r_seed = [np.random.default_rng(s) for s in
                             np.random.SeedSequence(seed).spawn(3)]
    p0 = base_pitch()
    path = sway_path(n, r_path, knock_scale=knock_scale)
    truths = [camera(p[0], p0 + p[1], p[2], p[3], p[4], p[5]) for p in path]

    # setup on frame 0 exactly as the product would: keypoints -> PnP -> paint fit
    t0 = time.time()
    f0 = render(truths[0], r_img, ss=ss, subpixel=subpixel)
    kps = {nm: tuple(np.array(uv) + r_seed.normal(0, seed_sigma, 2))
           for nm, uv in zip(court.KEYPOINTS_3D,
                             truths[0].project(list(court.LANDMARKS_3D.values())))
           if np.isfinite(uv).all() and 0 <= uv[0] < W and 0 <= uv[1] < H}
    seed_cam = camera3d.solve_pnp_seed(kps, (W, H)).camera
    setup = camera3d.fit_camera_checked(f0, seed_cam).camera
    setup_err = line_errors(truths[0], setup.ground_point)
    if verbose:
        print(f"setup: worst line {max(setup_err.values()) * 100:.2f} cm, "
              f"f {setup.f_px:.1f} (true {truths[0].f_px:.1f}), {time.time() - t0:.0f}s",
              flush=True)

    tracker = camtrack.CameraTracker(
        setup, cfg=camtrack.TrackConfig(far_lines=far_lines))
    Hb = setup.ground_homography()
    res = {"camtrack": [], "lock_step": []}
    jumps = {"camtrack": [], "lock_step": []}
    prev = {"camtrack": None, "lock_step": None, "true": None}
    status, locked, scope = [], [], []
    frame = f0
    for i, tc in enumerate(truths):
        if i:
            frame = render(tc, r_img, ss=ss, subpixel=subpixel)
        img8 = np.clip(frame, 0, 255).astype(np.uint8)
        st = tracker.step(img8, i / FPS)
        status.append(st.status)
        locked.append(bool(st.locked))
        scope.append(st.lock_scope)
        if i:
            A, _ = calibration.court_lock_step(np.dstack([img8] * 3), Hb)
            Hb = A @ Hb
        est = {"camtrack": (st.camera.ground_point, lambda g, c=st.camera: c.project(
                   np.column_stack([g, np.zeros(len(g))]))),
               "lock_step": (lambda uv, Hm=Hb: calibration.image_to_court(Hm, uv),
                             lambda g, Hm=Hb: calibration.court_to_image(Hm, g))}
        fb_true = far_baseline_px(lambda g: tc.project(np.column_stack([g, np.zeros(len(g))])))
        for arm, (to_g, to_img) in est.items():
            res[arm].append(line_errors(tc, to_g))
            fb = far_baseline_px(to_img)
            if prev[arm] is not None:
                d_est = fb - prev[arm]
                d_true = fb_true - prev["true"]
                jumps[arm].append((i, float(np.max(np.linalg.norm(d_est - d_true, axis=1)))))
            prev[arm] = fb
        prev["true"] = fb_true
        if verbose and i % 20 == 0:
            print(f"  frame {i:3d} {st.status:9s} camtrack worst "
                  f"{max(res['camtrack'][-1].values()) * 100:7.2f} cm | lock_step worst "
                  f"{max(res['lock_step'][-1].values()) * 100:7.2f} cm  "
                  f"({time.time() - t0:.0f}s)", flush=True)
    return {
        "stamp": {"tool": "tools/court_track_sim.py", "seed": seed, "n_frames": n, "fps": FPS,
                  "image": [W, H], "knock_scale": knock_scale, "mount_m": MOUNT_M, "setback_m": SETBACK_M,
                  "hfov_deg": HFOV_DEG, "seed_sigma_px": seed_sigma,
                  # the RESOLVED config the tracker ran with, not the class
                  # defaults: until 2026-09-22 this stamped TrackConfig() and so
                  # recorded far_lines=False on runs made with --far-lines
                  "tracker_cfg": dict(vars(tracker.cfg)),
                  "far_reach_px_720": camera3d.FAR_REACH_PX_720,
                  "far_tol_px_720": camera3d.FAR_TOL_PX_720,
                  "measured_against": "the exact synthetic camera that rendered each frame",
                  "supersample": ss, "subpixel": subpixel,
                  "renderer": f"flat court, 5 cm paint, {ss}x{ss} supersample, blur 0.9 px, "
                              "sensor noise, far fence with posts; no lens, no codec"},
        "paint_check_far_lines": far_lines,
        "setup_worst_m": max(setup_err.values()),
        "setup_check": setup.extra.get("paint_check"),
        "status": status,
        "locked": locked,
        "lock_scope": scope,
        "runs": {arm: {"frames": res[arm], "jumps": jumps[arm], "knock": int(KNOCK_S * FPS),
                       "locked": locked if arm == "camtrack" else None}
                 for arm in res},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--out", default=None)
    ap.add_argument("--knock-scale", type=float, default=1.0)
    ap.add_argument("--far-lines", action="store_true",
                    help="G8's far-line instrument (shipped OFF; see "
                         "camera3d.FAR_LINES_DEFAULT)")
    ap.add_argument("--subpixel", action="store_true",
                    help="CP1's render order; required for any far-line measurement")
    ap.add_argument("--ss", type=int, default=SS_DEFAULT,
                    help="renderer supersampling; 2 reproduces every pre-G8 number, "
                         "4 is what G8 needs to render sub-pixel paint at all")
    a = ap.parse_args()
    got = [run(s, a.n, knock_scale=a.knock_scale, ss=a.ss,
               subpixel=a.subpixel, far_lines=a.far_lines) for s in a.seeds]
    summ = {arm: summarise([g["runs"][arm] for g in got]) for arm in ("camtrack", "lock_step")}
    tag = "" if a.knock_scale == 1.0 else f"_knock{a.knock_scale:g}"
    tag += "" if a.ss == SS_DEFAULT else f"_ss{a.ss}"
    tag += "_sub" if a.subpixel else ""
    tag += "_far" if a.far_lines else ""
    out = Path(a.out or OUT / f"seeds{'-'.join(map(str, a.seeds))}_n{a.n}{tag}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summ, "runs": got}, indent=1), encoding="utf-8")
    for arm, s in summ.items():
        print(f"{arm:10s} worst p90 {s['worst_p90_m'] * 100:8.2f} cm  {s['verdict']:13s} "
              f"steady jump {s['max_steady_jump_px']:.2f} px (all {s['max_jump_px']:.2f})  "
              f"knock recovery {s['knock_recovery_frames']} frames")
        if "locked_frames" in s:
            print(f"    locked {s['locked_frames']}  locked-but-wrong(>10 cm) {s['locked_wrong']}  "
                  f"unlocked {s['unlocked_frames']}  worst-line p90 while locked "
                  f"{s['locked_worst_p90_m'] * 100:.2f} cm")
        for nm, v in s["lines"].items():
            print(f"    {nm:26s} p50 {v['p50'] * 100:8.2f}  p90 {v['p90'] * 100:8.2f}  "
                  f"max {v['max'] * 100:8.2f} cm")
    for g in got:
        st = g["status"]
        print(f"seed {g['stamp']['seed']}: setup worst line {g['setup_worst_m'] * 100:.2f} cm "
              f"(check {g['setup_check']}), "
              f"tracker status {({s: st.count(s) for s in sorted(set(st))})}")
    print("wrote", out)


if __name__ == "__main__":
    main()
