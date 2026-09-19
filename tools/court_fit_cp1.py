"""court_fit_cp1.py - CP1 stage 1: can a seeded whole-court fit to the PAINT place the court?

WHY THIS EXISTS
---------------
P8 C1 (tools/court_map_ceiling.py) showed a court model built from four corner
points misplaces the far baseline by metres at ~15 px of corner error. v1's court
is found AUTOMATICALLY (founder ruling 2026-09-17), and a detector's corners are
that rough. Route R1 (docs/evidence/court-precision-routes.md s5) says four rough
corners should only SEED a fit:
measure every painted line to sub-pixel precision in a narrow band around the
seeded projection, average a static window of frames, and solve ONE camera
(pose + focal length + lens distortion) that explains every line under the
regulation dimensions. CP1 (s7 of that file, plus its LEAD ADDENDUM) is the
pre-registered synthetic test of that route. This file is stage 1: renderer,
real-encoder harness, the R1 fit, the three instrument controls, arm P and arm
A3 (codec off).

WHAT IT MEASURES, AND AGAINST WHAT
----------------------------------
Measured against EXACT projected court geometry from a known synthetic camera
(C1's camera): the true ground coordinates of 11 points on each of C1's 14 line
halves. No labels, no model output.

Readouts, both scored exactly like C1 (worst of 11 points, perpendicular ground
error, p90 over trials):
  M - the FITTED MODEL: the true pixel of a ball on the line, back-projected to
      z=0 through the fitted camera.
  L - the MEASURED LINE: a straight line fitted to the measured paint centre of
      that half (in the fitted lens's undistorted frame), moved to the ITF
      reference edge by the model's projected half-width. Error = how far the
      ball must move along the ground normal before it crosses that line.

WHAT PINS THE COURT (rule 7): measured paint positions + the regulation doubles
court (ITF, positions to the OUTSIDE of lines, 5 cm paint) + planarity + a known,
centred principal point. The four rough corners only seed. Focal length and one division
distortion coefficient are FITTED, not given.

THE LENS MISMATCH IS DELIBERATE: the renderer distorts with Brown (k1, k2); the
fitter models distortion with the one-parameter DIVISION model, so it is not
grading its own lens model.

    cd backend && .venv/Scripts/python.exe ../tools/court_fit_cp1.py --arm ctl1 --n 20
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from scipy import ndimage, optimize
from scipy.special import ndtr

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import court_map_ceiling as C1                                    # noqa: E402
from court_camera import CORNERS, HFOV_DEG, SETBACK_M, frame_the_court  # noqa: E402
from swingvision import court as CT                               # noqa: E402
from swingvision import paintfit as PF                           # noqa: E402
from swingvision.paintfit import (                               # noqa: E402,F401
    NET_XM, NET_Y, PAINT_W, POST_HALF, POST_X, TAPE_H, FitConfig, PaintLine, TapeLine,
    _design, _F, _Fd, _features, _hline, _in_play, _visible_poly, centre_marks,
    PHI, make_stations, measure_line, paint_lines, r1_fit, tape_top)


W, H = 1920, 1080
HD = math.hypot(W / 2.0, H / 2.0)          # division-model radius normaliser (px)
MOUNT_M = 3.0
TAP_SIGMA_PRIMARY = round(C1.HUMAN_SIGMA_1920, 2)   # 14.78
BAR_M, KILL_M = C1.BAR_M, C1.KILL_M
OUT_DIR = REPO / "data" / "output" / "court_fit_cp1"
RENDER_VERSION = "cp1-render-5-smooth-kernel-sub2"
RENDER_SUB = 2          # jittered points per axis inside each 1/16 cell

# ---------------------------------------------------------------- scene -----
BROWN = (-0.030, 0.0056)        # f-normalised; ~30 px at the horizontal edge
SURFACE_DN, RUNOFF_DN = 95.0, 80.0
CONTRAST_RANGE = (60.0, 160.0)
PSF_RANGE = (0.7, 1.2)
# sigma is drawn uniformly from this grid (one cached render per value)
PSF_GRID = tuple(float(x) for x in np.round(np.arange(0.70, 1.2001, 0.05), 2))
NOISE_A, NOISE_B = 3.0 / 128.0, 1.0       # var = a*I + b -> sigma 2 DN at 128
MESH_PITCH, MESH_CORD = 0.0445, 0.004
FENCE_Y = CT.Y_FAR_BASELINE + 6.40
FENCE_TOP, RAIL_H = 4.0, 0.07
TRUSS_YS = (8.0, 14.0, 20.0, 26.0, 32.0, 38.0)
TRUSS_Z = (6.0, 6.3)
# material ids -> DN (3 = paint, coloured per trial)
SKY, SURF, RUNOFF, PAINT, TAPE, MESH, POST, FENCE, RAIL, TRUSS = range(10)
COLOUR = np.array([150, SURFACE_DN, RUNOFF_DN, 0, 220, 30, 40, 45, 120, 60], float)


# C1 line half -> (physical line, half)
HALF_MAP = {
    "near_doubles_sideline_L": ("doubles_L", "near"), "near_doubles_sideline_R": ("doubles_R", "near"),
    "near_singles_sideline_L": ("singles_L", "near"), "near_singles_sideline_R": ("singles_R", "near"),
    "far_doubles_sideline_L": ("doubles_L", "far"), "far_doubles_sideline_R": ("doubles_R", "far"),
    "far_singles_sideline_L": ("singles_L", "far"), "far_singles_sideline_R": ("singles_R", "far"),
    "near_centre_service": ("centre_service", "near"), "far_centre_service": ("centre_service", "far"),
    "near_baseline": ("near_baseline", "all"), "far_baseline": ("far_baseline", "all"),
    "near_service_line": ("near_service", "all"), "far_service_line": ("far_service", "all"),
}


# --------------------------------------------------------------- camera -----
# The camera, the seed and the R1 fit live in swingvision.paintfit (lifted
# verbatim apart from the image size becoming a parameter). This harness is
# 1920x1080 throughout, so these wrappers pin that size.
class Camera(PF.Camera):
    def __init__(self, C, yaw, pitch, roll, f, cx=W / 2.0, cy=H / 2.0,
                 brown=None, lam=0.0, wh=(W, H)):
        super().__init__(C, yaw, pitch, roll, f, cx, cy, brown, lam, wh=wh)

    @classmethod
    def from_params(cls, p, cx=W / 2.0, cy=H / 2.0, wh=(W, H)):
        return cls(p[0:3], p[3], p[4], p[5], p[6], cx, cy, None, p[7], wh=wh)


def seed_camera(corners_px, cx=W / 2.0, cy=H / 2.0):
    return PF.seed_camera(corners_px, cx, cy, (W, H))


def truth_camera(distortion=True, shift_v=0.0, height=MOUNT_M):
    got = frame_the_court(height, SETBACK_M, HFOV_DEG, W, H)
    kp, pitch_deg = got
    f = (W / 2.0) / math.tan(math.radians(HFOV_DEG) / 2.0)
    cam = Camera((CT.DOUBLES_WIDTH / 2.0, -SETBACK_M, height), 0.0,
                 math.radians(pitch_deg), 0.0, f, W / 2.0, H / 2.0 + shift_v,
                 BROWN if distortion else None)
    return cam, kp, pitch_deg


def lam_star(cam):
    """The division coefficient that best reproduces the TRUE Brown lens over
    the frame, with f and the principal point held at truth. The k1 error is
    reported against this; it is 0 when the render has no distortion."""
    if cam.brown is None:
        return 0.0
    rd = np.linspace(1.0, HD, 400)
    pts = np.column_stack([cam.cx + rd, np.full_like(rd, cam.cy)])
    ru_true = cam.undistort(pts)[:, 0] - cam.cx

    def cost(lam):
        return float((((rd / HD) / (1 + lam * (rd / HD) ** 2)) * HD - ru_true) @
                     (((rd / HD) / (1 + lam * (rd / HD) ** 2)) * HD - ru_true))
    return float(optimize.minimize_scalar(cost, bounds=(-0.5, 0.5), method="bounded",
                                          options={"xatol": 1e-9}).x)


# -------------------------------------------------------------- render ------
def materials(C, d, rects, clutter, marks):
    """Material id of each ray (C: camera centre, d: N x 3 directions)."""
    n = len(d)
    mat = np.full(n, SKY, np.uint8)
    tbest = np.full(n, np.inf)
    with np.errstate(divide="ignore", invalid="ignore"):
        tg = np.where(d[:, 2] < 0, -C[2] / d[:, 2], np.inf)
    gx = C[0] + tg * d[:, 0]
    gy = C[1] + tg * d[:, 1]
    hit = np.isfinite(tg)
    inside = hit & (gx >= CT.X_LEFT_DOUBLES) & (gx <= CT.X_RIGHT_DOUBLES) & \
        (gy >= CT.Y_NEAR_BASELINE) & (gy <= CT.Y_FAR_BASELINE)
    g = np.where(inside, SURF, RUNOFF).astype(np.uint8)
    for (x0, x1, y0, y1) in list(rects) + list(marks):
        g[hit & (gx >= x0) & (gx <= x1) & (gy >= y0) & (gy <= y1)] = PAINT
    mat[hit] = g[hit]
    tbest[hit] = tg[hit]
    if not clutter:
        return mat
    with np.errstate(divide="ignore", invalid="ignore"):
        # net plane
        tn = np.where(d[:, 1] > 0, (NET_Y - C[1]) / d[:, 1], np.inf)
        xn = C[0] + tn * d[:, 0]
        zn = C[2] + tn * d[:, 2]
        top = tape_top(np.clip(xn, POST_X[0], POST_X[1]))
        in_x = (xn >= POST_X[0]) & (xn <= POST_X[1]) & (tn < tbest)
        tape = in_x & (zn <= top) & (zn >= top - TAPE_H)
        mreg = in_x & (zn >= 0) & (zn < top - TAPE_H)
        cord = mreg & ((np.mod(xn, MESH_PITCH) < MESH_CORD) |
                       (np.mod(zn, MESH_PITCH) < MESH_CORD))
        post = (tn < tbest) & (zn >= 0) & (zn <= CT.NET_HEIGHT_POST + 0.05) & \
            ((np.abs(xn - POST_X[0]) <= POST_HALF) | (np.abs(xn - POST_X[1]) <= POST_HALF))
        for m, k in ((tape, TAPE), (cord, MESH), (post, POST)):
            mat[m] = k
            tbest[m] = tn[m]
        # back fence
        tf = np.where(d[:, 1] > 0, (FENCE_Y - C[1]) / d[:, 1], np.inf)
        xf = C[0] + tf * d[:, 0]
        zf = C[2] + tf * d[:, 2]
        fh = (tf < tbest) & (zf >= 0) & (zf <= FENCE_TOP) & (np.abs(xf - NET_XM) <= 18)
        rail = fh & ((zf >= FENCE_TOP - RAIL_H) | (np.mod(xf + 100.0, 3.0) < 0.08))
        mat[fh] = FENCE
        mat[rail] = RAIL
        tbest[fh] = tf[fh]
        # roof trusses
        for yk in TRUSS_YS:
            tt = np.where(d[:, 1] > 0, (yk - C[1]) / d[:, 1], np.inf)
            xt = C[0] + tt * d[:, 0]
            zt = C[2] + tt * d[:, 2]
            th = (tt < tbest) & (zt >= TRUSS_Z[0]) & (zt <= TRUSS_Z[1]) & \
                (np.abs(xt - NET_XM) <= 18)
            mat[th] = TRUSS
            tbest[th] = tt[th]
    return mat


def _edge_points(cam, rects, marks, clutter):
    """Dense 3-D points along every feature boundary, for flagging pixels that
    need supersampling (a 0.14 px line can hide between pixel corners)."""
    pts = []

    def seg(p, q, step):
        k = max(2, int(np.linalg.norm(np.subtract(q, p)) / step) + 1)
        t = np.linspace(0, 1, k)[:, None]
        pts.append((1 - t) * np.array(p, float) + t * np.array(q, float))
    for (x0, x1, y0, y1) in list(rects) + list(marks):
        for p, q in (((x0, y0, 0), (x1, y0, 0)), ((x0, y1, 0), (x1, y1, 0)),
                     ((x0, y0, 0), (x0, y1, 0)), ((x1, y0, 0), (x1, y1, 0))):
            seg(p, q, 0.004)
    # court boundary (surface/run-off) lies on paint edges already
    if clutter:
        xs = np.linspace(POST_X[0], POST_X[1], 4000)
        for dz in (0.0, -TAPE_H):
            pts.append(np.column_stack([xs, np.full_like(xs, NET_Y), tape_top(xs) + dz]))
        for px in POST_X:
            for dx in (-POST_HALF, POST_HALF):
                seg((px + dx, NET_Y, 0), (px + dx, NET_Y, 1.12), 0.005)
        for z in (0.0, FENCE_TOP - RAIL_H, FENCE_TOP):
            seg((NET_XM - 18, FENCE_Y, z), (NET_XM + 18, FENCE_Y, z), 0.01)
        for xk in np.arange(-100.0, 100.0, 3.0):
            for dx in (0.0, 0.08):
                if abs(xk + dx - NET_XM) <= 18:
                    seg((xk + dx, FENCE_Y, 0), (xk + dx, FENCE_Y, FENCE_TOP), 0.01)
        for yk in TRUSS_YS:
            for z in TRUSS_Z:
                seg((NET_XM - 18, yk, z), (NET_XM + 18, yk, z), 0.01)
    P = np.vstack(pts)
    uv, z = cam.to_undist(P)
    ok = z > 0.05
    return cam.distort(uv[ok])


class Coverage:
    """Per-PSF-sigma rendered maps: image = base[s] + (surface + contrast) * paint[s]."""

    def __init__(self, sigmas, base, paint, info):
        self.sigmas, self.base, self.paint, self.info = sigmas, base, paint, info


def coverage_key(cam, rects, marks, clutter, ss):
    blob = json.dumps({"v": RENDER_VERSION, "p": cam.params().round(12).tolist(),
                       "cxy": [cam.cx, cam.cy], "brown": cam.brown,
                       "rects": np.round(rects, 9).tolist(),
                       "marks": np.round(marks, 9).tolist(),
                       "clutter": clutter, "ss": ss, "sub": RENDER_SUB, "sig": list(PSF_GRID)}, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:16]


def _flags(cam, rects, marks, clutter):
    """Pixels whose footprint is not a single material, and the material at
    every pixel centre."""
    uu, vv = np.meshgrid(np.arange(W + 1) - 0.5, np.arange(H + 1) - 0.5)
    cuv = np.column_stack([uu.ravel(), vv.ravel()])
    cid = np.empty(len(cuv), np.uint8)
    netreg = np.zeros(len(cuv), bool)
    step = 1_000_000
    for i in range(0, len(cuv), step):
        d = cam.rays(cuv[i:i + step])
        cid[i:i + step] = materials(cam.C, d, rects, clutter, marks)
        if clutter:
            with np.errstate(divide="ignore", invalid="ignore"):
                tn = np.where(d[:, 1] > 0, (NET_Y - cam.C[1]) / d[:, 1], np.inf)
                zn = cam.C[2] + tn * d[:, 2]
                xn = cam.C[0] + tn * d[:, 0]
            netreg[i:i + step] = ((xn >= POST_X[0] - 0.1) & (xn <= POST_X[1] + 0.1) &
                                  (zn >= -0.05) & (zn <= 1.2))
    cid = cid.reshape(H + 1, W + 1)
    netreg = netreg.reshape(H + 1, W + 1) | np.isin(cid, (TAPE, MESH, POST))
    flag = ((cid[:-1, :-1] != cid[:-1, 1:]) | (cid[:-1, :-1] != cid[1:, :-1]) |
            (cid[:-1, :-1] != cid[1:, 1:]))
    flag |= netreg[:-1, :-1] | netreg[1:, 1:] | netreg[:-1, 1:] | netreg[1:, :-1]
    ep = _edge_points(cam, rects, marks, clutter)
    ei = np.round(ep).astype(int)
    ok = (ei[:, 0] >= 0) & (ei[:, 0] < W) & (ei[:, 1] >= 0) & (ei[:, 1] < H)
    em = np.zeros((H, W), bool)
    em[ei[ok, 1], ei[ok, 0]] = True
    flag |= ndimage.binary_dilation(em, np.ones((5, 5), bool))
    pc = np.column_stack([np.tile(np.arange(W, dtype=float), H),
                          np.repeat(np.arange(H, dtype=float), W)])
    pcid = np.empty(W * H, np.uint8)
    for i in range(0, len(pc), step):
        pcid[i:i + step] = materials(cam.C, cam.rays(pc[i:i + step]), rects, clutter, marks)
    return flag, pcid.reshape(H, W)


def _pix_kernel(sig, ss):
    """1-D pixel-box (x) Gaussian kernel at the fine cell-centre offsets
    (i + 0.5)/ss, i = -N .. N-1, normalised to sum 1."""
    N = int(math.ceil(ss * (0.5 + 4.0 * sig)))
    tt = (np.arange(-N, N) + 0.5) / ss
    k = PHI((tt + 0.5) / sig) - PHI((tt - 0.5) / sig)
    return N, (k / k.sum()).astype(np.float64)


def _stride_conv(f, K, N, ss, axis, n_out):
    """Convolve the fine array along `axis` with K and read it at pixel
    centres (fine index ss*j + ss/2 is the kernel's centre), edge-padded."""
    f = np.moveaxis(f, axis, -1)
    pad = [(0, 0)] * (f.ndim - 1) + [(N, N)]
    fp = np.pad(f, pad, mode="edge")
    out = np.empty(f.shape[:-1] + (n_out,), np.float64)
    step = 64
    for r in range(0, f.shape[0], step):
        win = np.lib.stride_tricks.sliding_window_view(fp[r:r + step], 2 * N, axis=-1)
        win = win[..., ss // 2:ss // 2 + ss * n_out:ss, :]
        out[r:r + step] = np.einsum("...k,k->...", win, K)
    return np.moveaxis(out, -1, axis)


def build_coverage(cam, rects, marks, clutter, ss=16, cache=True, verbose=False, strip=16,
                   sub=RENDER_SUB):
    """Render the scene as OPTICS THEN SENSOR.

    ss x ss stratified-jittered point samples per pixel give the scene's
    material at 1/ss px. The pixel value is that indicator integrated against
    K = pixel box (x) Gaussian PSF, a SMOOTH separable kernel, evaluated at the
    fine cell centres (midpoint rule: the only discretisation effect is an
    extra symmetric blur of variance 1/(12 ss^2)). Blurring AFTER binning to
    pixels (the literal order in s7) would erase the position of any line
    narrower than a pixel inside its pixel row."""
    key = coverage_key(cam, rects, marks, clutter, ss)
    path = OUT_DIR / "cache" / f"cov_{key}.npz"
    if cache and path.exists():
        z = np.load(path)
        return Coverage(tuple(z["sigmas"].tolist()), z["base"], z["paint"],
                        json.loads(str(z["info"])))
    t0 = time.time()
    flag, pcid = _flags(cam, rects, marks, clutter)
    colour_nopaint = COLOUR.copy()
    colour_nopaint[PAINT] = 0.0
    kernels = [_pix_kernel(sg, ss) for sg in PSF_GRID]
    margin = int(math.ceil(max(k[0] for k in kernels) / ss)) + 1
    # evaluate every pixel within the kernel reach of a flagged pixel exactly
    evalm = ndimage.binary_dilation(flag, np.ones((3, 3), bool))
    base = np.zeros((len(PSF_GRID), H, W), np.float32)
    paint = np.zeros((len(PSF_GRID), H, W), np.float32)
    off = (np.arange(ss) + 0.5) / ss - 0.5
    jr = np.random.default_rng(20260917)
    for r0 in range(0, H, strip):
        r1 = min(r0 + strip, H)
        a0, a1 = max(r0 - margin, 0), min(r1 + margin, H)
        mid = np.repeat(np.repeat(pcid[a0:a1], ss, 0), ss, 1)
        fi, fj = np.nonzero(evalm[a0:a1])
        fb = colour_nopaint[mid].astype(np.float32)
        fpaint = (mid == PAINT).astype(np.float32)
        del mid
        # stratified: sub x sub jittered points inside every 1/ss cell
        so = ((np.arange(sub) + 0.5) / sub - 0.5) / ss
        sou, sov = np.meshgrid(so, so)
        sou, sov = sou.ravel(), sov.ravel()
        nsub = sub * sub
        chunk = max(1, 8000 // nsub)
        for c0 in range(0, len(fi), chunk):
            ii, jj = fi[c0:c0 + chunk], fj[c0:c0 + chunk]
            n = len(ii)
            su = (jj[:, None, None, None] + off[None, None, :, None] + sou[None, None, None, :] +
                  jr.uniform(-0.5 / (ss * sub), 0.5 / (ss * sub), (n, ss, ss, nsub)))
            sv = ((ii + a0)[:, None, None, None] + off[None, :, None, None] + sov[None, None, None, :] +
                  jr.uniform(-0.5 / (ss * sub), 0.5 / (ss * sub), (n, ss, ss, nsub)))
            m = materials(cam.C, cam.rays(np.column_stack([su.ravel(), sv.ravel()])),
                          rects, clutter, marks).reshape(n, ss, ss, nsub)
            rr = (ii * ss)[:, None, None] + np.arange(ss)[None, :, None]
            cc = (jj * ss)[:, None, None] + np.arange(ss)[None, None, :]
            fb[rr, cc] = colour_nopaint[m].mean(-1)
            fpaint[rr, cc] = (m == PAINT).mean(-1)
        # rows outside the image are edge-replicated so every strip sees `margin`
        padlo, padhi = r0 - margin - a0, r1 + margin - a1
        pads = ((ss * max(0, -padlo), ss * max(0, padhi)), (0, 0))
        fb = np.pad(fb, pads, mode="edge")
        fpaint = np.pad(fpaint, pads, mode="edge")
        for k, (N, K) in enumerate(kernels):
            for src, dst in ((fb, base), (fpaint, paint)):
                u = _stride_conv(src, K, N, ss, 1, W)
                # u's fine row 0 is pixel row r0 - margin; convolve every row and
                # keep the strip (edge padding only touches the discarded margins)
                v = _stride_conv(u, K, N, ss, 0, u.shape[0] // ss)
                dst[k, r0:r1] = v[margin:margin + (r1 - r0)]
        del fb, fpaint
        if verbose and r0 % 160 == 0:
            print(f"  strip {r0}/{H} {time.time() - t0:.0f}s", flush=True)
    info = {"key": key, "flagged_px": int(flag.sum()), "evaluated_px": int(evalm.sum()),
            "ss": ss, "sub": sub, "order": "psf(x)pixel kernel on the 1/ss jittered indicator",
            "build_s": round(time.time() - t0, 1)}
    if verbose:
        print("coverage", info, flush=True)
    if cache:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, sigmas=np.array(PSF_GRID), base=base, paint=paint,
                 info=json.dumps(info))
    return Coverage(tuple(PSF_GRID), base, paint, info)


def clean_image(cov, contrast, psf):
    k = int(np.argmin(np.abs(np.asarray(cov.sigmas) - psf)))
    assert abs(cov.sigmas[k] - psf) < 1e-9, "psf must be drawn from PSF_GRID"
    return cov.base[k].astype(np.float64) + (SURFACE_DN + contrast) * cov.paint[k]


def noisy_frames(clean, nframes, rng, noise=True):
    sd = np.sqrt(NOISE_A * np.clip(clean, 0, None) + NOISE_B).astype(np.float32)
    c32 = clean.astype(np.float32)
    for _ in range(nframes):
        if not noise:
            # zero noise means zero quantisation noise too: an undithered 8-bit
            # round is a ~0.3 DN STRUCTURED error, not a property of the fit
            yield c32
            continue
        fr = c32 + rng.standard_normal(c32.shape, dtype=np.float32) * sd
        yield np.clip(np.rint(fr), 0, 255).astype(np.uint8)


X265 = {"codec": "libx265", "profile": "main", "preset": "medium", "bitrate": "16M",
        "fps": 60, "keyint": 60, "vbv_maxrate_kbps": 16000, "vbv_bufsize_kbps": 16000,
        "pix_fmt": "yuv420p", "range": "Y plane passed through"}

# A SECOND, NAMED profile - not an edit of the one above. qa isolated CP1's
# run-to-run scatter to the encoder itself (2026-09-18 audit s6: four encodes of a
# byte-identical 30-frame array differed on ~1.8 M of 2.07 M pixels, and one arm-P
# trial's far baseline spread 0.66 cm over three repeats). Thread count is the
# cause, so `pools` and `frame-threads` are pinned to 1 and WPP is off; CRF
# replaces the VBV rate control, whose lookahead state is also thread-dependent,
# and keyint 1 makes every frame intra so no frame depends on another.
#
# ANY RUN UNDER THIS PROFILE IS A DIFFERENT SCENE. All-intra at CRF 18 is a
# different, and easier, compression than 16 Mbps VBV with a 60-frame GOP. Numbers
# from it are NOT comparable with CP1 stage 1, G1 or G7 and must not be re-based
# onto them (hard rules 2 and 7). It exists so that an A/B inside itself is not
# measuring the encoder's thread scheduler. Pre-registered: G8, Part B.
X265_DETERMINISTIC = {"codec": "libx265", "profile": "main", "preset": "slow", "crf": 18,
                      "fps": 60, "keyint": 1, "threads": 1,
                      "x265_extra": "pools=1:frame-threads=1:wpp=0",
                      "pix_fmt": "yuv420p", "range": "Y plane passed through",
                      "NOT_COMPARABLE_WITH": "CP1 stage 1, G1, G7 (different scene)"}

CODEC_PROFILES = {"cp1": X265, "deterministic": X265_DETERMINISTIC}


def _encode_argv(cfg, fn):
    """ffmpeg argv for one codec profile - the RESOLVED settings, so the stamp and
    the encode can never disagree (the provenance trap, docs/TRAPS.md)."""
    common = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "yuv420p",
              "-s", f"{W}x{H}", "-r", str(cfg["fps"]), "-i", "-", "-c:v", "libx265",
              "-profile:v", cfg["profile"], "-preset", cfg["preset"]]
    if "crf" in cfg:
        rate = ["-crf", str(cfg["crf"])]
        params = (f"keyint={cfg['keyint']}:min-keyint={cfg['keyint']}:"
                  f"{cfg['x265_extra']}:log-level=error")
        common += ["-threads", str(cfg["threads"])]
    else:
        rate = ["-b:v", cfg["bitrate"]]
        params = (f"keyint={cfg['keyint']}:min-keyint={cfg['keyint']}:"
                  f"vbv-maxrate={cfg['vbv_maxrate_kbps']}:"
                  f"vbv-bufsize={cfg['vbv_bufsize_kbps']}:log-level=error")
    return common + rate + ["-x265-params", params, "-pix_fmt", "yuv420p", str(fn)]


def codec_mean(frames, workdir, cfg=None):
    """Encode with REAL ffmpeg libx265, decode, and return the mean decoded luma
    plus the achieved bitrate. `cfg` defaults to the CP1 profile."""
    cfg = cfg or X265
    fn = Path(workdir) / "clip.hevc"
    uvb = np.full((H // 2) * (W // 2) * 2, 128, np.uint8).tobytes()
    enc = subprocess.Popen(_encode_argv(cfg, fn), stdin=subprocess.PIPE)
    nf = 0
    for fr in frames:
        enc.stdin.write(fr.tobytes())
        enc.stdin.write(uvb)
        nf += 1
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError("x265 encode failed")
    kbps = fn.stat().st_size * 8 / (nf / cfg["fps"]) / 1000.0
    dec = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(fn), "-f", "rawvideo",
                          "-pix_fmt", "yuv420p", "-"], capture_output=True, check=True)
    fsz = W * H * 3 // 2
    raw = np.frombuffer(dec.stdout, np.uint8)
    got = len(raw) // fsz
    if got != nf:
        raise RuntimeError(f"decoded {got} frames, expected {nf}")
    acc = np.zeros((H, W), np.float64)
    for i in range(got):
        acc += raw[i * fsz:i * fsz + W * H].reshape(H, W)
    return acc / got, kbps



# ------------------------------------------------------------- readouts -----
def _fit_line_undist(pu, sig_c, iters=4):
    w = 1.0 / np.maximum(sig_c, 0.01) ** 2
    rw = np.ones_like(w)
    for _ in range(iters):
        ww = w * rw
        c = (ww[:, None] * pu).sum(0) / ww.sum()
        d = pu - c
        cov = (ww[:, None, None] * d[:, :, None] * d[:, None, :]).sum(0)
        evals, evecs = np.linalg.eigh(cov)
        m = evecs[:, 0]
        r = d @ m / np.maximum(sig_c, 0.01)
        rw = np.minimum(1.0, 3.0 / np.maximum(np.abs(r), 1e-9))
    return c, m


def readouts(fcam, meas, lines, render_cam, ref_cam, n_pts=11):
    """Per C1 line half: M and L ground errors (worst of n_pts, metres), L image
    error (px, for net-tape capture), and far-baseline signed image offsets."""
    by = {L.name: L for L in lines}
    Hf = fcam.homography()
    out = {}
    for name, a, b, nrm in C1.lines():
        pname, half = HALF_MAP[name]
        L = by[pname]
        nrm = np.array(nrm, float)
        t = np.linspace(0, 1, n_pts)[:, None]
        xy = (1 - t) * np.array(a) + t * np.array(b)
        uv = render_cam.project_ground(xy)
        gM = fcam.ground(uv)
        eM = float(np.nanmax(np.abs((gM - xy) @ nrm))) if np.isfinite(gM).all() else math.inf
        eL, eimg, nst = math.inf, math.inf, 0
        m = meas.get(pname)
        if m is not None and len(m["pts"]):
            gy = m["g"]
            if half == "near":
                sel = gy[:, 1] < NET_Y
            elif half == "far":
                sel = gy[:, 1] > NET_Y
            else:
                sel = np.ones(len(gy), bool)
            nst = int(sel.sum())
            if nst >= FitConfig.min_half_stations:
                pu = fcam.undistort(m["pts"][sel])
                c0, mv = _fit_line_undist(pu, m["sig_c"][sel])
                lc = _hline(Hf, L.a, L.b)
                lr = _hline(Hf, L.a + L.n * L.ref_off, L.b + L.n * L.ref_off)
                # orient everything along the image of +n
                gmid = (L.a + L.b) / 2
                dn = fcam.to_undist(np.array([[*(gmid + L.n * 0.01), 0]]))[0] - \
                    fcam.to_undist(np.array([[*gmid, 0]]))[0]
                dn = dn[0]
                if mv @ dn < 0:
                    mv = -mv
                if lc[:2] @ dn < 0:
                    lc = -lc
                if lr[:2] @ dn < 0:
                    lr = -lr

                def gfun(p):
                    q = fcam.undistort(render_cam.project_ground(p))
                    qh = np.column_stack([q, np.ones(len(q))])
                    return (q - c0) @ mv - (qh @ lc - qh @ lr)
                g0 = gfun(xy)
                g1 = gfun(xy + 0.01 * nrm)
                slope = (g1 - g0) / 0.01
                sstar = -g0 / slope
                eL = float(np.max(np.abs(sstar)))
                shifted = render_cam.project_ground(xy + sstar[:, None] * nrm)
                eimg = float(np.max(np.linalg.norm(shifted - uv, axis=1)))
        out[name] = {"M": eM, "L": eL, "L_img_px": eimg, "L_stations": nst}
    # far-baseline signed vertical image offsets vs the REFERENCE camera
    L = by["far_baseline"]
    dense = np.linspace(0, 1, 400)[:, None]
    gref = (1 - dense) * L.a + dense * L.b
    vref = ref_cam.project_ground(gref)
    order = np.argsort(vref[:, 0])
    fb = {"L_offset_px": math.nan, "M_offset_px": math.nan}
    m = meas.get("far_baseline")
    if m is not None and len(m["pts"]):
        vt = np.interp(m["pts"][:, 0], vref[order, 0], vref[order, 1])
        fb["L_offset_px"] = float(np.median(m["pts"][:, 1] - vt))
    ref_edge = (1 - dense) * (L.a + L.n * L.ref_off) + dense * (L.b + L.n * L.ref_off)
    fb["M_offset_px"] = float(np.median(fcam.project_ground(ref_edge)[:, 1] -
                                        ref_cam.project_ground(ref_edge)[:, 1]))
    return out, fb


# ---------------------------------------------------------------- arms ------
ARMS = {
    # arm: distortion, codec, clutter, noise, seed sigma, frames, shift_v
    "P":      dict(distortion=True, codec=True, clutter=True, noise=True,
                   seed_sigma=TAP_SIGMA_PRIMARY, frames=30, shift_v=0.0),
    "A3":     dict(distortion=True, codec=False, clutter=True, noise=True,
                   seed_sigma=TAP_SIGMA_PRIMARY, frames=30, shift_v=0.0),
    "ctl1":   dict(distortion=False, codec=False, clutter=False, noise=False,
                   seed_sigma=0.0, frames=30, shift_v=0.0),
    "ctl2":   dict(distortion=False, codec=False, clutter=False, noise=True,
                   seed_sigma=TAP_SIGMA_PRIMARY, frames=30, shift_v=0.0),
    "ctl2s0": dict(distortion=False, codec=False, clutter=False, noise=True,
                   seed_sigma=0.0, frames=30, shift_v=0.0),
    "ctl3a":  dict(distortion=False, codec=False, clutter=False, noise=False,
                   seed_sigma=0.0, frames=30, shift_v=0.10),
    "ctl3b":  dict(distortion=False, codec=False, clutter=False, noise=True,
                   seed_sigma=TAP_SIGMA_PRIMARY, frames=30, shift_v=0.10),
}

_COV = {}


def _coverage_for(arm_cfg):
    k = (arm_cfg["distortion"], arm_cfg["clutter"], arm_cfg["shift_v"])
    if k not in _COV:
        rcam, _, _ = truth_camera(arm_cfg["distortion"], arm_cfg["shift_v"])
        lines = paint_lines()
        _COV[k] = build_coverage(rcam, [L.rect() for L in lines], centre_marks(),
                                 arm_cfg["clutter"])
    return _COV[k]


def run_trial(job):
    arm, trial, seed = job["arm"], job["trial"], job["seed"]
    a = ARMS[arm]
    codec_cfg = CODEC_PROFILES[job.get("codec_profile", "cp1")]
    t0 = time.time()
    ss = np.random.SeedSequence([seed, trial])
    r_scene, r_seed, r_noise = [np.random.default_rng(x) for x in ss.spawn(3)]
    contrast = float(r_scene.uniform(*CONTRAST_RANGE))
    psf = float(PSF_GRID[int(r_scene.integers(len(PSF_GRID)))])
    rcam, _, _ = truth_camera(a["distortion"], a["shift_v"])
    ref_cam, _, _ = truth_camera(a["distortion"], 0.0)
    seed_err = r_seed.normal(0.0, 1.0, (4, 2)) * a["seed_sigma"]
    true_corners = {n: rcam.project_ground([CT.LANDMARKS[n]])[0] for n in CORNERS}
    seed_corners = {n: (true_corners[n] + seed_err[i]).tolist() for i, n in enumerate(CORNERS)}
    cov = _coverage_for(a)
    clean = clean_image(cov, contrast, psf)
    frames = noisy_frames(clean, a["frames"], r_noise, a["noise"])
    kbps = None
    t_codec = 0.0
    if a["codec"]:
        tc = time.time()
        with tempfile.TemporaryDirectory(dir=job.get("tmp")) as td:
            img, kbps = codec_mean(frames, td, codec_cfg)
        t_codec = time.time() - tc
    else:
        acc = np.zeros((H, W))
        nf = 0
        for fr in frames:
            acc += fr
            nf += 1
        # (a noise-free arm yields float frames; codec arms always carry noise)
        img = acc / nf
    row = {"trial": trial, "contrast": contrast, "psf": psf, "kbps": kbps,
           "seed_err_px": seed_err.tolist()}
    tf = time.time()
    try:
        fcam, meas, lines, sig, kappa = r1_fit(img, seed_corners, FitConfig, rcam.cx, H / 2.0)
        per, fb = readouts(fcam, meas, lines, rcam, ref_cam)
        row.update({"ok": True, "lines": per, "far_bl": fb, "sig_est": sig, "kappa": kappa,
                    "n_meas": {k: int(len(v["pts"])) for k, v in meas.items()},
                    "f_fit": fcam.f, "lam_fit": fcam.lam, "cam_h": float(fcam.C[2]),
                    "params": fcam.params().tolist()})
    except Exception as ex:                       # a failed fit is a FAILURE row
        row.update({"ok": False, "error": repr(ex)})
    row["t_fit_s"] = round(time.time() - tf, 2)
    row["t_codec_s"] = round(t_codec, 2)
    row["t_total_s"] = round(time.time() - t0, 2)
    return row


def git_sha():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                              text=True, timeout=15).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def git_dirty():
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--", "tools/court_fit_cp1.py"],
                             cwd=REPO, capture_output=True, text=True, timeout=15).stdout
        return bool(out.strip())
    except Exception:
        return True


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return v if math.isfinite(v) else ("inf" if v > 0 else ("-inf" if v < 0 else "nan"))
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    return o


def summarise(rows, arm):
    a = ARMS[arm]
    rcam, _, _ = truth_camera(a["distortion"], 0.0)
    lst = lam_star(rcam)
    ok = [r for r in rows if r["ok"]]
    names = [n for n, *_ in C1.lines()]

    def q(v, p):
        v = np.asarray(v, float)
        return float(np.percentile(v, p)) if len(v) else math.nan
    lines = {}
    for n in names:
        M = [r["lines"][n]["M"] if r["ok"] else math.inf for r in rows]
        Lr = [r["lines"][n]["L"] if r["ok"] else math.inf for r in rows]
        im = [r["lines"][n]["L_img_px"] if r["ok"] else math.inf for r in rows]
        lines[n] = {"M_p50": q(M, 50), "M_p90": q(M, 90), "M_max": q(M, 100),
                    "L_p50": q(Lr, 50), "L_p90": q(Lr, 90), "L_max": q(Lr, 100),
                    "capture_rate": float(np.mean(np.asarray(im) > 2.0)),
                    "L_missing": int(sum(1 for r in rows if not r["ok"] or
                                         not math.isfinite(r["lines"][n]["L"])))}

    def verdict(p90M, p90L):
        worst = max(p90M, p90L)
        return "PASS" if worst <= BAR_M else ("KILL" if worst > KILL_M else "INDETERMINATE")
    for n in names:
        lines[n]["verdict"] = verdict(lines[n]["M_p90"], lines[n]["L_p90"])
    f_true = (W / 2.0) / math.tan(math.radians(HFOV_DEG) / 2.0)
    fe = [r["f_fit"] - f_true for r in ok]
    le = [r["lam_fit"] - lst for r in ok]
    hh = [r["cam_h"] for r in ok]
    fbL = [r["far_bl"]["L_offset_px"] for r in ok]
    fbM = [r["far_bl"]["M_offset_px"] for r in ok]
    return {
        "arm": arm, "n": len(rows), "fit_failures": len(rows) - len(ok),
        "lines": lines,
        "pass_all": all(v["verdict"] == "PASS" for v in lines.values()),
        "f_true_px": f_true, "lam_star": lst,
        "f_err_px": {"p50": q(np.abs(fe), 50), "p90": q(np.abs(fe), 90), "mean": q(fe, 50)},
        "f_err_pct_p90": q(np.abs(fe), 90) / f_true * 100 if fe else math.nan,
        "lam_err": {"p50": q(np.abs(le), 50), "p90": q(np.abs(le), 90)},
        "cam_h": {"p50": q(hh, 50), "p10": q(hh, 10), "p90": q(hh, 90),
                  "abs_err_p90": q(np.abs(np.asarray(hh) - MOUNT_M), 90)},
        "far_bl_L_offset_px": {"mean": float(np.nanmean(fbL)) if fbL else math.nan,
                               "abs_p50": q(np.abs(fbL), 50), "abs_p90": q(np.abs(fbL), 90)},
        "far_bl_M_offset_px": {"mean": float(np.nanmean(fbM)) if fbM else math.nan,
                               "abs_p50": q(np.abs(fbM), 50), "abs_p90": q(np.abs(fbM), 90)},
        "sig_est_p50": q([r["sig_est"] for r in ok], 50),
        "kbps_p50": q([r["kbps"] for r in rows if r["kbps"]], 50),
        "t_trial_s_p50": q([r["t_total_s"] for r in rows], 50),
    }


def stamp(arm, n, seed, workers, codec_profile="cp1"):
    a = ARMS[arm]
    rcam, kp, pitch = truth_camera(a["distortion"], a["shift_v"])
    return {
        "tool": "tools/court_fit_cp1.py", "commit": git_sha(),
        "tool_dirty_at_run": git_dirty(),
        "python": sys.version.split()[0], "numpy": np.__version__,
        "platform": platform.platform(), "arm": arm, "arm_config": a,
        "n": n, "seed": seed, "workers": workers,
        "measured_against": "exact projected court geometry from a known synthetic "
                            "camera (C1's): true ground coordinates of 11 points on "
                            "each of C1's 14 line halves. No labels, no model output.",
        "court_pinned_by": "measured paint positions + regulation doubles court (ITF, "
                           "outside-edge convention, 5 cm paint) + planarity + known "
                           "centred principal point + one paint/step ratio and one blur "
                           "measured on the near lines. The four-corner first guess only "
                           "seeds. f and one division k1 are fitted.",
        "seed": "a rough first guess of the four doubles corners, as an automatic "
                "court detector would supply it: exact corners + per-axis Gaussian "
                "error of seed_sigma px @1920 (the repo's auto-detector corner error "
                "has been of the same order, ~6.4 px @640 = ~19 px @1920)",
        "camera": {"mount_m": MOUNT_M, "setback_m": SETBACK_M, "hfov_deg": HFOV_DEG,
                   "pitch_deg": pitch, "f_px": rcam.f, "cx": rcam.cx, "cy": rcam.cy,
                   "brown": rcam.brown, "corners_px_undistorted": kp},
        "scene": {"paint_w": PAINT_W, "surface_dn": SURFACE_DN, "runoff_dn": RUNOFF_DN,
                  "contrast_range": CONTRAST_RANGE, "psf_grid": PSF_GRID,
                  "render_order": "PSF then pixel footprint (1/4 px grid), 16x16 jittered samples",
                  "noise_var": f"{NOISE_A}*I+{NOISE_B}", "supersample": 16,
                  "render_version": RENDER_VERSION, "net_tape_h": TAPE_H,
                  "mesh": [MESH_PITCH, MESH_CORD], "fence_y": FENCE_Y,
                  "truss_ys": TRUSS_YS},
        "codec": CODEC_PROFILES[codec_profile] if a["codec"] else None,
        "codec_profile": codec_profile if a["codec"] else None,
        "fitter": FitConfig.as_dict(),
        "bars": {"pass_m": BAR_M, "kill_m": KILL_M, "capture_px": 2.0},
    }


def run_arm(arm, n, seed, workers, out, verbose=True, codec_profile="cp1"):
    from concurrent.futures import ProcessPoolExecutor
    _coverage_for(ARMS[arm])          # build/cached once, before forking workers
    tmp = OUT_DIR / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    jobs = [{"arm": arm, "trial": i, "seed": seed, "tmp": str(tmp),
             "codec_profile": codec_profile} for i in range(n)]
    t0 = time.time()
    rows = []
    if workers <= 1:
        for j in jobs:
            rows.append(run_trial(j))
    else:
        with ProcessPoolExecutor(workers) as ex:
            for k, r in enumerate(ex.map(run_trial, jobs, chunksize=1)):
                rows.append(r)
                if verbose and (k + 1) % 25 == 0:
                    print(f"  {arm}: {k + 1}/{n}  {time.time() - t0:.0f}s", flush=True)
    wall = time.time() - t0
    summ = summarise(rows, arm)
    summ["wall_s"] = wall
    res = {"stamp": stamp(arm, n, seed, workers, codec_profile), "summary": summ,
           "rows": rows}
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_jsonable(res), indent=1), encoding="utf-8")
    return res


def print_summary(s):
    print(f"arm {s['arm']}  n={s['n']}  fit failures={s['fit_failures']}  "
          f"wall={s.get('wall_s', 0):.0f}s  trial p50={s['t_trial_s_p50']:.1f}s")
    print(f"{'line':<26}{'M p50':>8}{'M p90':>8}{'L p50':>8}{'L p90':>8}{'capt':>6}  verdict")
    for n, v in s["lines"].items():
        print(f"{n:<26}{v['M_p50']:8.4f}{v['M_p90']:8.4f}{v['L_p50']:8.4f}{v['L_p90']:8.4f}"
              f"{v['capture_rate']:6.2f}  {v['verdict']}")
    print(f"f err p90 {s['f_err_px']['p90']:.2f} px ({s['f_err_pct_p90']:.2f}%)  "
          f"lam* {s['lam_star']:.5f} err p90 {s['lam_err']['p90']:.5f}  "
          f"cam h p50 {s['cam_h']['p50']:.3f} (abs err p90 {s['cam_h']['abs_err_p90']:.3f})")
    print(f"far BL offset L mean {s['far_bl_L_offset_px']['mean']:+.4f} |p90| "
          f"{s['far_bl_L_offset_px']['abs_p90']:.4f} px; M mean "
          f"{s['far_bl_M_offset_px']['mean']:+.4f} |p90| {s['far_bl_M_offset_px']['abs_p90']:.4f}"
          f"  sigma_est {s['sig_est_p50']:.2f}  kbps {s['kbps_p50']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--out", default=None)
    ap.add_argument("--codec-profile", default="cp1", choices=sorted(CODEC_PROFILES),
                    help="cp1 reproduces every stamped CP1/G1/G7 number; "
                         "deterministic pins the encoder and is a DIFFERENT scene (G8)")
    args = ap.parse_args()
    tag = "" if args.codec_profile == "cp1" else f"_{args.codec_profile}"
    out = args.out or str(OUT_DIR / f"{args.arm}_seed{args.seed}_n{args.n}{tag}.json")
    res = run_arm(args.arm, args.n, args.seed, args.workers, out,
                  codec_profile=args.codec_profile)
    print_summary(res["summary"])
    print("wrote", out)


if __name__ == "__main__":
    main()
