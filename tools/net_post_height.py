"""The net POSTS as a RIGID, off-plane camera-height estimator.

What this is, and why it is not just more net tape
--------------------------------------------------
`tools/net_tape_height.py` measures the white net tape at `z = 0.914` m and turns
its image row into a camera height that the four clicked corners never saw. It
works (AGREE 13/15, `docs/evidence/net-tape-camera-height-consistency.md`) and it
is the only shipped check that reads a point OFF the ground plane - which is the
whole reason it catches errors that every ground-plane statistic misses
(`docs/evidence/independent-calibration-references.md`).

It has one confound it cannot resolve from its own evidence: **a net sags.**

A POST does not. It is rigid, regulation `NET_HEIGHT_POST = 1.07` m, at a known
court x (`X_LEFT_POST = -0.914`, `X_RIGHT_POST = 11.884`). So a post height is
off-plane like the tape and free of the tape's confound, and the SIGN of any
post-vs-tape disagreement is informative: from

    row = horizon + (ground_row - horizon) * (H - h) / H

the estimator inverts to `H_est = H_true * h_nominal / h_true`, so a net that
sags (`h_true < 0.914` at the centre) makes the TAPE read the camera HIGHER than
truth, never lower. `tape > post` is consistent with slack; `tape < post` is not.

NEITHER NUMBER IS GROUND TRUTH, and this is NOT A GATE. Four autonomous
accept/reject gates have failed in this family. Nothing here rejects a
calibration, edits a calibration, or changes a fitted height. It prints a second
number for the human who confirms the calibration at setup.

How the post top is searched
----------------------------
Identical reparametrisation to the tape tool, and for the same reason: do not
search image rows, search HEIGHT. Under the FITTED pose, projecting the post
point at a fake height `h'` lands exactly where the real 1.07 m post top would
land if the true camera height were

    H = 1.07 * H_fitted / h'

because the row offset from the horizon depends on `h` and `H` only through
`h/H`. A 1-D sweep over `h'` therefore generates precisely the family of
candidate post tops - correct column, correct lean, correct foreshortening - and
the response peak converts straight to a camera height.

The response, rotated 90 degrees from the tape's
------------------------------------------------
The tape is a bright horizontal band and is matched with `min(on-above,
on-below)`. A post is a VERTICAL bar whose sign is not knowable a priori: dark
against sky, light against a dark fence. So the per-point response is

    postness(h') = max( min(on-left, on-right), min(left-on, right-on) )

sampled along the LOCAL PERPENDICULAR to the projected post (not along image
columns - a post leans under perspective), with the tape's own window widths
scaled by `frame_height/720`.

The measurand is the post TOP, which is not a peak in `postness` but a STEP in
it: post below, background above. So

    R(h') = mean(postness just BELOW h') - mean(postness just ABOVE h')

over a +-4 px scaled window, and the post top is the peak of `R`.

The post BASE is on `z = 0`. It carries NO off-plane information and is never
used in the height - it is reported only to price the instrument (predicted post
pixel length) and to state framing.

Refusal is the point
--------------------
Rules PRE-REGISTERED in `.claude/journals/backend-dev.md` before this file was
written, and reported rather than dropped (rule 10):

  P0 no camera pose, or degenerate horizon-vs-net-ground rows
  P1 >= 60% of the swept grid on-frame AND the +-window at the peak fully on-frame
  P2 peak edge response >= MIN_EDGE grey levels
  P3 robust z of the peak over the sweep >= MIN_Z
  P4 best rival peak >= RIVAL_SEP_PX away scores <= RIVAL_FRAC of the best
  P5 if BOTH posts pass, their implied heights must agree to <= MAX_SPREAD_PX
     of top row; two rigid posts that disagree means I cannot say which is a post
  P6 RESOLVABILITY: predicted post pixel length >= MIN_POST_PX, ABSOLUTE not
     scaled - an edge measured on a 6 px bar is not measurable at any sensor
     resolution. This is the rule `demo30` (47.9 px net span, 5.5%/px) should
     have hit in the tape run and did not.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import warnings

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO / "backend") not in sys.path:
    sys.path.insert(0, str(REPO / "backend"))

import net_anchor_check as nac                      # noqa: E402  (tools/ is script dir)
import net_tape_height as nth                       # noqa: E402
import render_corner_audit as rca                   # noqa: E402
from swingvision import calibration, court as _court  # noqa: E402

# ---- pre-registered constants (journal, before any sweep) --------------------
H_MIN, H_MAX = 0.90, 12.0   # camera heights the sweep covers, metres
ROW_STEP_PX = 0.5           # sweep resolution, px of post-top row
EDGE_WIN_PX = 4.0           # +- window of the step-edge response, scaled
MIN_GRID_FRAC = 0.60        # P1
MIN_EDGE = 4.0              # P2, grey levels
MIN_Z = 4.0                 # P3, robust z
RIVAL_SEP_PX = 5.0          # P4
RIVAL_FRAC = 0.75           # P4
MAX_SPREAD_PX = 3.0         # P5, scaled by frame_height/720
MIN_POST_PX = 10.0          # P6, ABSOLUTE px, deliberately unscaled


def _perp_samples(plate, pts, s):
    """`postness` along a projected post: a bar differing from BOTH neighbours.

    Sampled on the local perpendicular to the curve, so a leaning post is
    handled exactly. Windows are net_tape_height's, rotated 90 degrees."""
    w_on = max(1, int(round(1.5 * s)))
    bg_in = w_on + max(2, int(round(2.5 * s)))
    bg_out = bg_in + max(3, int(round(4.0 * s)))
    p = np.asarray(pts, float)
    d = np.gradient(p, axis=0)
    n = np.stack([-d[:, 1], d[:, 0]], axis=1)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.divide(n, np.where(ln < 1e-9, np.nan, ln))

    def band(k0, k1):
        acc = [nth._bilinear(plate, p[:, 0] + k * n[:, 0], p[:, 1] + k * n[:, 1])
               for k in range(k0, k1 + 1)]
        st = np.stack(acc, 0)
        # An all-NaN column is a legitimate off-frame sample, not an error; NaN is
        # the intended answer and P1 counts them.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmean(st, axis=0)

    on = band(-w_on, w_on)
    right = band(bg_in, bg_out)
    left = band(-bg_out, -bg_in)
    bright = np.minimum(on - left, on - right)
    dark = np.minimum(left - on, right - on)
    return np.maximum(bright, dark)


def _step_response(post_ness, k):
    """R[j] = mean(postness BELOW j) - mean(postness ABOVE j). Grid is increasing
    height, so 'below the top' is smaller index."""
    n = len(post_ness)
    out = np.full(n, np.nan)
    for j in range(k, n - k):
        lo = post_ness[j - k:j]
        hi = post_ness[j + 1:j + 1 + k]
        if np.isfinite(lo).all() and np.isfinite(hi).all():
            out[j] = float(lo.mean() - hi.mean())
    return out


def measure_post(plate, geo, name, img_wh, hfov_deg, h_fitted, px_per_m, s):
    """One post. Returns a dict with either `post_H_m` or `refused`."""
    x_post = _court.NET_POST_BASES[name][0]
    out = {"post": name, "post_H_m": None, "refused": None, "peak_edge": None,
           "z": None, "rival_frac": None, "grid_frac": None, "post_px": None}

    base = geo["post_bases"].get(name)
    top = geo["post_tops"].get(name)
    if base is None or top is None:
        out["refused"] = "P0 post top unprojectable (no pose / behind camera)"
        return out
    post_px = float(np.hypot(top[0] - base[0], top[1] - base[1]))
    out["post_px"] = round(post_px, 1)
    w, h = img_wh
    out["base_in_frame"] = bool(0 <= base[0] < w and 0 <= base[1] < h)
    out["top_in_frame"] = bool(0 <= top[0] < w and 0 <= top[1] < h)
    if post_px < MIN_POST_PX:
        out["refused"] = (f"P6 post images {post_px:.1f} px tall "
                          f"< {MIN_POST_PX:.0f} px - not resolvable")
        return out

    hp_lo = _court.NET_HEIGHT_POST * h_fitted / H_MAX
    hp_hi = _court.NET_HEIGHT_POST * h_fitted / H_MIN
    step = ROW_STEP_PX / px_per_m
    grid = np.arange(hp_lo, hp_hi + step, step)
    if len(grid) < 40:
        out["refused"] = "P0 search grid degenerate"
        return out

    pts = calibration.project_court_3d(
        geo["H"], img_wh, [(float(x_post), _court.NET_Y, float(z)) for z in grid],
        hfov_deg)
    if pts is None:
        out["refused"] = "P0 post column unprojectable"
        return out
    pn = _perp_samples(plate, np.asarray(pts, float), s)
    frac = float(np.isfinite(pn).mean())
    out["grid_frac"] = round(frac, 2)
    if frac < MIN_GRID_FRAC:
        out["refused"] = (f"P1 only {100 * frac:.0f}% of the sweep on-frame "
                          f"(< {100 * MIN_GRID_FRAC:.0f}%)")
        return out

    k = max(2, int(round(EDGE_WIN_PX * s / ROW_STEP_PX)))
    resp = _step_response(pn, k)
    if not np.isfinite(resp).any():
        out["refused"] = "P1 no candidate top has a full window on-frame"
        return out
    j = int(np.nanargmax(resp))
    best_hp, best = float(grid[j]), float(resp[j])
    out["peak_edge"] = round(best, 2)
    out["peak_h_prime_m"] = round(best_hp, 3)
    out.update(_diagnose(grid, resp, px_per_m))
    fin = resp[np.isfinite(resp)]
    out["z"] = round(nth._robust_z(fin, best), 2)
    far = np.abs((grid - best_hp) * px_per_m) >= RIVAL_SEP_PX
    m = far & np.isfinite(resp)
    rival = float(np.nanmax(resp[m])) if m.any() else -1e9
    out["rival_frac"] = round(rival / best, 3) if best > 1e-6 else None

    if best < MIN_EDGE:
        out["refused"] = f"P2 edge {best:.1f} < {MIN_EDGE} grey levels"
        return out
    if out["z"] < MIN_Z:
        out["refused"] = f"P3 robust z {out['z']:.1f} < {MIN_Z}"
        return out
    if out["rival_frac"] is not None and out["rival_frac"] > RIVAL_FRAC:
        out["refused"] = (f"P4 rival edge {out['rival_frac']:.2f} of the peak "
                          f"more than {RIVAL_SEP_PX:.0f} px away - ambiguous")
        return out
    out["h_prime_m"] = round(best_hp, 4)
    out["post_H_m"] = round(_court.NET_HEIGHT_POST * h_fitted / best_hp, 3)
    return out


def _diagnose(grid, resp, px_per_m):
    """POST-HOC DIAGNOSTICS. Never read by any refusal rule and never by the
    height. They answer the one question a pass/fail cannot: does a post produce
    a detectable step AT ALL at the place the calibration itself predicts? That
    reference is the fitted height, so nothing here is evidence ABOUT the fitted
    height - it is instrument characterisation only."""
    fin = np.isfinite(resp)
    if not fin.any():
        return {}
    j = int(np.argmin(np.abs(grid - _court.NET_HEIGHT_POST)))
    if not fin[j]:
        return {"diag_true_on_grid": False}
    vals = resp[fin]
    d = {"diag_true_on_grid": True,
         "diag_edge_at_predicted": round(float(resp[j]), 2),
         "diag_z_at_predicted": round(nth._robust_z(vals, float(resp[j])), 2),
         "diag_pctile_at_predicted": round(100.0 * float((vals < resp[j]).mean()), 1)}
    idx = np.where(fin)[0]
    r = resp[idx]
    loc = idx[1:-1][(r[1:-1] > r[:-2]) & (r[1:-1] > r[2:])]
    if len(loc):
        d["diag_px_to_nearest_local_max"] = round(
            float(np.min(np.abs(grid[loc] - grid[j])) * px_per_m), 1)
    return d


def measure_post_height(plate, kp, img_wh, hfov_deg, h_fitted):
    """Both posts, then the clip-level combination and P5."""
    w, h = img_wh
    s = max(1.0, h / 720.0)
    out = {"post_H_m": None, "refused": None, "posts": []}
    if hfov_deg is None:
        out["refused"] = "P0 no camera pose (hfov unrecoverable)"
        return out
    geo = nac.net_anchor_geometry(kp, img_wh, hfov_deg)
    hz, gr = geo["horizon_row"], geo["net_ground_row"]
    if hz is None or gr is None or abs(gr - hz) < 5.0:
        out["refused"] = "P0 horizon/net-ground rows degenerate"
        return out
    px_per_m = abs(gr - hz) / float(h_fitted)          # rows per metre of height
    out["horizon_row"], out["net_ground_row"] = hz, gr
    # PRICE THE INSTRUMENT, reported whether or not the clip is confident:
    # dH/drow = H^2 / (h * (ground - horizon)); as a percentage of H that is
    # 100 * H / (h * (ground - horizon)). Post h = 1.07, tape h = 0.914, so the
    # post is 0.914/1.07 = 0.854x the tape PER PIXEL of row error.
    out["pct_per_px_post"] = round(
        100.0 * h_fitted / (_court.NET_HEIGHT_POST * abs(gr - hz)), 2)
    out["pct_per_px_tape"] = round(
        100.0 * h_fitted / (_court.NET_HEIGHT_CENTER * abs(gr - hz)), 2)

    for name in sorted(_court.NET_POST_BASES):
        out["posts"].append(measure_post(plate, geo, name, img_wh, hfov_deg,
                                         h_fitted, px_per_m, s))
    ok = [p for p in out["posts"] if p["post_H_m"] is not None]
    if not ok:
        out["refused"] = "; ".join(f"{p['post']}: {p['refused']}" for p in out["posts"])
        return out
    if len(ok) == 2:
        # P5 in the common currency: convert the height disagreement to px of top
        # row via dH/drow = H^2 / (h * (ground - horizon)).
        hm = float(np.mean([p["post_H_m"] for p in ok]))
        dH = abs(ok[0]["post_H_m"] - ok[1]["post_H_m"])
        spread = dH * _court.NET_HEIGHT_POST * abs(gr - hz) / (hm * hm)
        out["spread_px"] = round(float(spread), 2)
        if spread > MAX_SPREAD_PX * s:
            out["refused"] = (f"P5 the two posts disagree by {spread:.1f} px of top "
                              f"row (> {MAX_SPREAD_PX * s:.1f})")
            return out
    out["n_posts"] = len(ok)
    out["post_H_m"] = round(float(np.mean([p["post_H_m"] for p in ok])), 3)
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
    plate = nth.clean_plate(video)
    if plate is None:
        return {"tag": tag, "status": "NO FRAME"}
    plate, nframes = plate
    h, w = plate.shape
    stamped = blob.get("_audit", {}).get("img_wh")
    if stamped and (stamped[0] != w or stamped[1] != h):
        sx, sy = w / float(stamped[0]), h / float(stamped[1])
        kp = {n: (kp[n][0] * sx, kp[n][1] * sy) for n in nac.CORNERS}
    hfov = nac.hfov_for(kp, w, h)
    h_fit = nth.fitted_height(kp, w, h)
    if h_fit is None:
        return {"tag": tag, "status": "NO FIT"}
    m = measure_post_height(plate, kp, (w, h), hfov, h_fit)
    row = {"tag": tag, "status": "measured", "video": video.name, "wh": [w, h],
           "plate_frames": nframes, "fitted_H_m": round(h_fit, 3), "hfov_deg": hfov}
    row.update(m)
    if m["post_H_m"] is not None:
        d = m["post_H_m"] - h_fit
        row["delta_m"] = round(d, 3)
        row["delta_pct"] = round(100.0 * d / h_fit, 1)
        row["agree_10pct"] = abs(row["delta_pct"]) <= 10.0
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pts", nargs="*", default=None)
    ap.add_argument("--out", default=str(REPO / "data" / "output" / "corner_audit"
                                         / "net_post_height.json"))
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
              f"fit {r.get('fitted_H_m')} post {r.get('post_H_m')} "
              f"d% {r.get('delta_pct')} :: {r.get('refused') or r.get('note') or ''}",
              flush=True)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1))
    ok = [r for r in rows if r.get("post_H_m") is not None]
    agree = [r for r in ok if r["agree_10pct"]]
    print(f"\nconfident post heights: {len(ok)}   within 10%: {len(agree)}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
