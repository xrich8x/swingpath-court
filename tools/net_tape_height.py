"""The net TAPE as an INDEPENDENT camera-height estimator.

What this is
------------
The camera height stamped on every calibration in this repo is a CONSEQUENCE of
the four clicked doubles corners: 4 points fix the homography, `cam_fit_quad`
projects that onto the camera manifold, and out falls `Cz`. Nothing about that
number is checked against the world. This tool produces a SECOND height from a
different piece of evidence - the image row of the white net tape, which is
never clicked - so the two can be compared.

For a pinhole at height H, a point h metres above the ground at the same depth
images at

    row = horizon + (ground_row - horizon) * (H - h) / H

so, given the horizon and the net's GROUND row (both from the homography) and
the OBSERVED tape row,

    H = h / (1 - (tape_row - horizon) / (ground_row - horizon)),   h = 0.914 m

NEITHER NUMBER IS GROUND TRUTH. The fitted height assumes the clicks are right;
the tape height assumes the net is regulation and the tape row was measured
right. A disagreement says at least one is wrong, never which. This tool
measures the disagreement. It does not resolve it, and it never edits a
calibration.

How the tape row is searched - the reparametrisation that makes this exact
--------------------------------------------------------------------------
Do NOT search image rows directly: the net images as a sloped, curved line under
perspective and camera roll, so "row 522" is only meaningful at one column.
Instead search HEIGHT. Under the FITTED camera pose, projecting the net line at a
fake height h' lands exactly where the real 0.914 m tape would land if the true
camera height were

    H = 0.914 * H_fitted / h'

(because the row offset from the horizon depends on h and H only through h/H).
So a 1-D sweep over h', reusing `calibration.project_court_3d` with the FITTED
hfov, generates precisely the family of candidate tape curves - correct columns,
correct slope, correct curvature - and the response peak converts straight to a
camera height. Every clip's search covers the same H range, so the estimator
cannot be accused of having been steered toward its own clip's fitted answer.

The response is qa's method (docs/evidence/net-anchor-qa-verification.md §3):
mean brightness on a clean frame, across DISJOINT column ranges. Three changes,
each to remove a way the eye or a single profile can be fooled:
  * clean PLATE, not one frame - per-pixel median of several frames, so a player,
    a ball or a racquet standing on the net line cannot make the band;
  * a bright-BAND matched filter, `min(on - above, on - below)`, so a region that
    is merely bright (a bright far court above the net) cannot score; the tape
    must be brighter than BOTH of its neighbourhoods;
  * three disjoint column ranges inside the central 50% of the net, which must
    AGREE, so a single-column fluke or a local bright object cannot carry it.

Refusal is the point
--------------------
"I cannot measure this tape" is a correct and useful answer; a confidently wrong
row is worse than silence, because the whole value of this estimator is that it
is independent. The refusal rules are PRE-REGISTERED in
`.claude/journals/backend-dev.md` before the sweep was run:

  R1 all three column ranges valid, >= MIN_COLS sampled points each, on-frame
  R2 peak band contrast >= MIN_SCORE grey levels
  R3 robust z of the peak over the whole sweep >= MIN_Z
  R4 the best rival peak >= RIVAL_SEP px away scores <= RIVAL_FRAC of the best
  R5 the three ranges' peaks agree to <= MAX_SPREAD_PX (in a common column)

Every pixel window scales by frame_height/720, per the project rule.

Known limits, stated because they bound what a disagreement can mean
--------------------------------------------------------------------
* A net that is NOT at regulation height, or that sags, breaks the estimator
  outright: club, park and clay nets sag, and a sagging centre reads as a LOWER
  camera. The estimator cannot tell a sagging net from a wrong calibration.
* The horizon and the ground row still come from the clicks. This is independent
  in the sense that it adds an observation the clicks did not determine; it is
  not independent of the homography.
* h is taken as 0.914 m across the central 50% of the net. A parabolic cord to
  1.07 m at the posts is at most ~0.75% higher at the edge of that window, which
  is far below the effects being looked for.
* The response peaks on the brightest horizontal band in the search range. On a
  clip where the tape is invisible and a fence rail is not, R2-R5 are all that
  stand between it and a wrong answer.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import cv2
import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO / "backend") not in sys.path:
    sys.path.insert(0, str(REPO / "backend"))

import net_anchor_check as nac                      # noqa: E402  (tools/ is script dir)
import render_corner_audit as rca                   # noqa: E402
from swingvision import calibration, court as _court  # noqa: E402

# ---- pre-registered constants ------------------------------------------------
PLATE_FRAMES = 7          # clean plate = per-pixel median of this many frames
PLATE_SPAN = 600          # spread over at most this many frames from the start
N_SAMPLES = 120           # court-x samples inside the search window
N_GROUPS = 3              # disjoint column ranges
CENTRAL_FRAC = 0.50       # of the doubles width, centred on the net centre
H_MIN, H_MAX = 0.90, 12.0  # camera heights the sweep covers, metres
ROW_STEP_PX = 0.5         # sweep resolution at the frame-centre column
MIN_COLS = 20             # R1
MIN_SCORE = 4.0           # R2, grey levels
MIN_Z = 4.0               # R3, robust z
RIVAL_SEP_PX = 5.0        # R4
RIVAL_FRAC = 0.75         # R4
MAX_SPREAD_PX = 3.0       # R5, scaled by frame_height/720


def clean_plate(video, n=PLATE_FRAMES, span=PLATE_SPAN):
    """Per-pixel median of n frames spread over the first `span` frames.

    Sequential decode only - `CAP_PROP_POS_FRAMES` seeking is the thing this
    project has ruled out on device and there is no reason to depend on it here
    either. The median kills anything that moved; the tape does not move."""
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return None
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    last = min(span, total - 1) if total > 0 else span
    idx = sorted({int(round(i * last / max(1, n - 1))) for i in range(n)})
    want, got, i = set(idx), [], 0
    while i <= max(idx):
        ok, fr = cap.read()
        if not ok:
            break
        if i in want:
            got.append(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32))
        i += 1
    cap.release()
    if not got:
        return None
    return np.median(np.stack(got, 0), axis=0), len(got)


def _bilinear(img, xs, ys):
    """Bilinear sample; NaN outside the frame."""
    h, w = img.shape
    x0 = np.floor(xs).astype(int)
    y0 = np.floor(ys).astype(int)
    ok = (x0 >= 0) & (x0 < w - 1) & (y0 >= 0) & (y0 < h - 1) & np.isfinite(xs) & np.isfinite(ys)
    out = np.full(xs.shape, np.nan, np.float32)
    if not ok.any():
        return out
    xi, yi = x0[ok], y0[ok]
    fx, fy = (xs[ok] - xi).astype(np.float32), (ys[ok] - yi).astype(np.float32)
    v = (img[yi, xi] * (1 - fx) * (1 - fy) + img[yi, xi + 1] * fx * (1 - fy)
         + img[yi + 1, xi] * (1 - fx) * fy + img[yi + 1, xi + 1] * fx * fy)
    out[ok] = v
    return out


def _band_score(plate, pts, s):
    """Bright-band matched filter at the projected curve `pts`.

    min(on - above, on - below): the tape must be brighter than BOTH sides, so a
    merely-bright region cannot score. Windows scale by frame_height/720."""
    w_on = max(1, int(round(1.5 * s)))
    bg_in = w_on + max(2, int(round(2.5 * s)))
    bg_out = bg_in + max(3, int(round(4.0 * s)))
    xs, ys = pts[:, 0], pts[:, 1]
    on = np.nanmean(np.stack([_bilinear(plate, xs, ys + d)
                              for d in range(-w_on, w_on + 1)], 0), axis=0)
    above = np.nanmean(np.stack([_bilinear(plate, xs, ys - d)
                                 for d in range(bg_in, bg_out + 1)], 0), axis=0)
    below = np.nanmean(np.stack([_bilinear(plate, xs, ys + d)
                                 for d in range(bg_in, bg_out + 1)], 0), axis=0)
    good = np.isfinite(on) & np.isfinite(above) & np.isfinite(below)
    if int(good.sum()) < MIN_COLS:
        return None, int(good.sum())
    return float(min(np.mean(on[good] - above[good]),
                     np.mean(on[good] - below[good]))), int(good.sum())


def _robust_z(vals, peak):
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med)))
    sd = 1.4826 * mad
    return float("inf") if sd < 1e-6 else (peak - med) / sd


def measure_tape_height(plate, kp, img_wh, hfov_deg, h_fitted):
    """Sweep candidate camera heights; return the tape-implied height or a refusal."""
    w, h = img_wh
    s = max(1.0, h / 720.0)
    out = {"tape_H_m": None, "refused": None, "groups": [], "peak_score": None,
           "z": None, "rival_frac": None, "spread_px": None, "n_cols": 0}
    if hfov_deg is None:
        out["refused"] = "R0 no camera pose (hfov unrecoverable)"
        return out
    geo = nac.net_anchor_geometry(kp, img_wh, hfov_deg)
    hz, gr = geo["horizon_row"], geo["net_ground_row"]
    if hz is None or gr is None or abs(gr - hz) < 5.0:
        out["refused"] = "R0 horizon/net-ground rows degenerate"
        return out
    px_per_m = abs(gr - hz) / float(h_fitted)          # rows per metre of height
    half = CENTRAL_FRAC * (_court.X_RIGHT_DOUBLES - _court.X_LEFT_DOUBLES) / 2.0
    xs = np.linspace(_court.X_CENTER - half, _court.X_CENTER + half, N_SAMPLES)
    groups = np.array_split(np.arange(N_SAMPLES), N_GROUPS)   # disjoint column ranges

    hp_lo = _court.NET_HEIGHT_CENTER * h_fitted / H_MAX
    hp_hi = _court.NET_HEIGHT_CENTER * h_fitted / H_MIN
    step = ROW_STEP_PX / px_per_m
    grid = np.arange(hp_lo, hp_hi + step, step)
    if len(grid) < 20:
        out["refused"] = "R0 search grid degenerate"
        return out

    curves, scores = [], []
    for hp in grid:
        pts = calibration.project_court_3d(
            geo["H"], img_wh, [(float(x), _court.NET_Y, float(hp)) for x in xs], hfov_deg)
        curves.append(None if pts is None else np.asarray(pts, float))
    per_group = np.full((N_GROUPS, len(grid)), np.nan)
    ncols = np.zeros(N_GROUPS, int)
    for j, pts in enumerate(curves):
        if pts is None:
            continue
        for g, idx in enumerate(groups):
            sc, n = _band_score(plate, pts[idx], s)
            if sc is not None:
                per_group[g, j] = sc
                ncols[g] = max(ncols[g], n)
    out["n_cols"] = int(ncols.min())
    valid = [g for g in range(N_GROUPS)
             if np.isfinite(per_group[g]).sum() > 20 and ncols[g] >= MIN_COLS]
    if len(valid) < N_GROUPS:
        out["refused"] = (f"R1 only {len(valid)}/{N_GROUPS} column ranges usable "
                          f"(min cols {int(ncols.min())})")
        return out

    peaks, peak_scores = [], []
    for g in range(N_GROUPS):
        v = per_group[g]
        j = int(np.nanargmax(v))
        peaks.append(float(grid[j]))
        peak_scores.append(float(v[j]))
    out["groups"] = [{"h_prime_m": round(p, 4),
                      "tape_H_m": round(_court.NET_HEIGHT_CENTER * h_fitted / p, 3),
                      "score": round(sc, 2)}
                     for p, sc in zip(peaks, peak_scores)]
    out["peak_score"] = round(float(min(peak_scores)), 2)
    out["spread_px"] = round(float((max(peaks) - min(peaks)) * px_per_m), 2)

    pooled = np.nanmean(per_group, axis=0)
    jp = int(np.nanargmax(pooled))
    best_hp, best = float(grid[jp]), float(pooled[jp])
    out["z"] = round(_robust_z(pooled[np.isfinite(pooled)], best), 2)
    far = np.abs((grid - best_hp) * px_per_m) >= RIVAL_SEP_PX
    rival = float(np.nanmax(pooled[far])) if np.isfinite(pooled[far]).any() else -1e9
    out["rival_frac"] = round(rival / best, 3) if best > 1e-6 else None

    if out["peak_score"] < MIN_SCORE:
        out["refused"] = f"R2 band contrast {out['peak_score']:.1f} < {MIN_SCORE} grey levels"
        return out
    if out["z"] < MIN_Z:
        out["refused"] = f"R3 robust z {out['z']:.1f} < {MIN_Z}"
        return out
    if out["rival_frac"] is not None and out["rival_frac"] > RIVAL_FRAC:
        out["refused"] = (f"R4 rival band {out['rival_frac']:.2f} of the peak "
                          f"more than {RIVAL_SEP_PX:.0f} px away - ambiguous")
        return out
    if out["spread_px"] > MAX_SPREAD_PX * s:
        out["refused"] = (f"R5 column ranges disagree by {out['spread_px']:.1f} px "
                          f"(> {MAX_SPREAD_PX * s:.1f})")
        return out
    out["tape_H_m"] = round(_court.NET_HEIGHT_CENTER * h_fitted / best_hp, 3)
    out["tape_row_center"] = round(float(hz + (gr - hz) * (1.0 - _court.NET_HEIGHT_CENTER
                                                           / out["tape_H_m"])), 1)
    out["horizon_row"], out["net_ground_row"] = hz, gr
    out["model_tape_row"] = geo["net_tape_row"]
    return out


def run_one(pts_path):
    tag = pts_path.stem.replace("_pts", "")
    blob = json.loads(pts_path.read_text(encoding="utf-8"))
    kp = {k: blob[k] for k in nac.CORNERS if k in blob}
    if len(kp) < 4:
        return {"tag": tag, "status": "SKIP", "note": f"only {len(kp)}/4 named corners"}
    video = rca.find_video(tag)
    if video is None:
        return {"tag": tag, "status": "NO VIDEO"}
    plate = clean_plate(video)
    if plate is None:
        return {"tag": tag, "status": "NO FRAME"}
    plate, nframes = plate
    h, w = plate.shape
    # Same rescale render_corner_audit.py applies: clicks may be stamped at a
    # different resolution than the decoded frame.
    stamped = blob.get("_audit", {}).get("img_wh")
    if stamped and (stamped[0] != w or stamped[1] != h):
        sx, sy = w / float(stamped[0]), h / float(stamped[1])
        kp = {n: (kp[n][0] * sx, kp[n][1] * sy) for n in nac.CORNERS}
    hfov = nac.hfov_for(kp, w, h)
    h_fit = fitted_height(kp, w, h)
    if h_fit is None:
        return {"tag": tag, "status": "NO FIT"}
    m = measure_tape_height(plate, kp, (w, h), hfov, h_fit)
    row = {"tag": tag, "status": "measured", "video": video.name, "wh": [w, h],
           "plate_frames": nframes, "fitted_H_m": round(h_fit, 3), "hfov_deg": hfov}
    row.update(m)
    if m["tape_H_m"] is not None:
        d = m["tape_H_m"] - h_fit
        row["delta_m"] = round(d, 3)
        row["delta_pct"] = round(100.0 * d / h_fit, 1)
        row["agree_10pct"] = abs(row["delta_pct"]) <= 10.0
    return row


def fitted_height(kp, w, h):
    from swingvision import courtfit
    fit = courtfit.cam_fit_quad({n: kp[n] for n in nac.CORNERS}, calibration,
                                _court, w, h, allow_roll=True)
    return None if fit is None else float(fit[3][2])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pts", nargs="*", default=None)
    ap.add_argument("--out", default=str(REPO / "data" / "output" / "corner_audit"
                                         / "net_tape_height.json"))
    args = ap.parse_args()
    files = ([pathlib.Path(p) for p in args.pts] if args.pts
             else sorted((REPO / "data").rglob("*_pts.json")))
    rows = []
    for f in files:
        try:
            r = run_one(f)
        except Exception as e:                          # noqa: BLE001
            r = {"tag": f.stem, "status": "ERROR", "note": repr(e)[:140]}
        rows.append(r)
        print(f"{r['tag']:26s} {r['status']:9s} "
              f"fit {r.get('fitted_H_m')} tape {r.get('tape_H_m')} "
              f"d% {r.get('delta_pct')} :: {r.get('refused') or r.get('note') or ''}",
              flush=True)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1))
    ok = [r for r in rows if r.get("tape_H_m") is not None]
    agree = [r for r in ok if r["agree_10pct"]]
    print(f"\nconfident tape rows: {len(ok)}   within 10%: {len(agree)}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
