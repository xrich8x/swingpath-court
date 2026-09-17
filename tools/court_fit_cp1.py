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

W, H = 1920, 1080
HD = math.hypot(W / 2.0, H / 2.0)          # division-model radius normaliser (px)
MOUNT_M = 3.0
TAP_SIGMA_PRIMARY = round(C1.HUMAN_SIGMA_1920, 2)   # 14.78
BAR_M, KILL_M = C1.BAR_M, C1.KILL_M
OUT_DIR = REPO / "data" / "output" / "court_fit_cp1"
RENDER_VERSION = "cp1-render-5-smooth-kernel-sub2"
RENDER_SUB = 2          # jittered points per axis inside each 1/16 cell

# ---------------------------------------------------------------- scene -----
PAINT_W = 0.05
BROWN = (-0.030, 0.0056)        # f-normalised; ~30 px at the horizontal edge
SURFACE_DN, RUNOFF_DN = 95.0, 80.0
CONTRAST_RANGE = (60.0, 160.0)
PSF_RANGE = (0.7, 1.2)
# sigma is drawn uniformly from this grid (one cached render per value)
PSF_GRID = tuple(float(x) for x in np.round(np.arange(0.70, 1.2001, 0.05), 2))
NOISE_A, NOISE_B = 3.0 / 128.0, 1.0       # var = a*I + b -> sigma 2 DN at 128
NET_Y = CT.NET_Y
POST_X = (CT.X_LEFT_POST, CT.X_RIGHT_POST)
NET_XM = (POST_X[0] + POST_X[1]) / 2.0
TAPE_H = 0.05
MESH_PITCH, MESH_CORD = 0.0445, 0.004
POST_HALF = 0.05
FENCE_Y = CT.Y_FAR_BASELINE + 6.40
FENCE_TOP, RAIL_H = 4.0, 0.07
TRUSS_YS = (8.0, 14.0, 20.0, 26.0, 32.0, 38.0)
TRUSS_Z = (6.0, 6.3)
# material ids -> DN (3 = paint, coloured per trial)
SKY, SURF, RUNOFF, PAINT, TAPE, MESH, POST, FENCE, RAIL, TRUSS = range(10)
COLOUR = np.array([150, SURFACE_DN, RUNOFF_DN, 0, 220, 30, 40, 45, 120, 60], float)


def tape_top(x):
    half = (POST_X[1] - POST_X[0]) / 2.0
    return (CT.NET_HEIGHT_CENTER + (CT.NET_HEIGHT_POST - CT.NET_HEIGHT_CENTER)
            * ((np.asarray(x, float) - NET_XM) / half) ** 2)


class PaintLine:
    """One PHYSICAL painted line: its centreline, width, and where the ITF
    reference edge and the run-off side are, along the C1 ground normal n."""

    def __init__(self, name, a, b, width, ref_off, outer, n):
        self.name, self.width = name, width
        self.a, self.b = np.array(a, float), np.array(b, float)
        self.ref_off, self.outer = ref_off, outer
        self.n = np.array(n, float)

    def rect(self):
        lo = np.minimum(self.a, self.b) - np.abs(self.n) * self.width / 2.0
        hi = np.maximum(self.a, self.b) + np.abs(self.n) * self.width / 2.0
        return (lo[0], hi[0], lo[1], hi[1])


def paint_lines(width=PAINT_W, bw=PAINT_W):
    X, Y = (1.0, 0.0), (0.0, 1.0)
    xl, xr = CT.X_LEFT_DOUBLES, CT.X_RIGHT_DOUBLES
    sl, sr, xc = CT.X_LEFT_SINGLES, CT.X_RIGHT_SINGLES, CT.X_CENTER
    y0, y1 = CT.Y_NEAR_BASELINE, CT.Y_FAR_BASELINE
    ns, fs = CT.Y_NEAR_SERVICE, CT.Y_FAR_SERVICE
    h = width / 2.0
    return [
        PaintLine("near_baseline", (xl, y0 + bw / 2), (xr, y0 + bw / 2), bw, -bw / 2, -1, Y),
        PaintLine("far_baseline", (xl, y1 - bw / 2), (xr, y1 - bw / 2), bw, +bw / 2, +1, Y),
        PaintLine("doubles_L", (xl + h, y0), (xl + h, y1), width, -h, -1, X),
        PaintLine("doubles_R", (xr - h, y0), (xr - h, y1), width, +h, +1, X),
        PaintLine("singles_L", (sl + h, y0), (sl + h, y1), width, -h, 0, X),
        PaintLine("singles_R", (sr - h, y0), (sr - h, y1), width, +h, 0, X),
        PaintLine("near_service", (sl, ns + h), (sr, ns + h), width, -h, 0, Y),
        PaintLine("far_service", (sl, fs - h), (sr, fs - h), width, +h, 0, Y),
        PaintLine("centre_service", (xc, ns), (xc, fs), width, 0.0, 0, X),
    ]


def centre_marks(bw=PAINT_W, width=PAINT_W):
    xc = CT.X_CENTER
    return [(xc - width / 2, xc + width / 2, bw, bw + 0.10),
            (xc - width / 2, xc + width / 2, CT.Y_FAR_BASELINE - bw - 0.10,
             CT.Y_FAR_BASELINE - bw)]


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
class Camera:
    """Pinhole camera in swingvision court metres (x width, y length, z up).
    yaw/pitch/roll follow C1's true_projector (pitch = tilt down). Lens is
    either Brown (k1, k2) in f-normalised coords, or division `lam` in
    HD-normalised coords, or none."""

    def __init__(self, C, yaw, pitch, roll, f, cx=W / 2.0, cy=H / 2.0,
                 brown=None, lam=0.0):
        self.C = np.asarray(C, float)
        self.yaw, self.pitch, self.roll = float(yaw), float(pitch), float(roll)
        self.f, self.cx, self.cy = float(f), float(cx), float(cy)
        self.brown, self.lam = brown, float(lam)
        cyw, syw = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cr, sr = math.cos(roll), math.sin(roll)
        fwd0 = np.array([syw, cyw, 0.0])
        right0 = np.array([cyw, -syw, 0.0])
        ez = np.array([0.0, 0.0, 1.0])
        fwd = cp * fwd0 - sp * ez
        up = sp * fwd0 + cp * ez
        right = cr * right0 + sr * up
        up2 = -sr * right0 + cr * up
        self.R = np.stack([right, -up2, fwd])

    def params(self):
        return np.array([*self.C, self.yaw, self.pitch, self.roll, self.f, self.lam])

    @classmethod
    def from_params(cls, p, cx=W / 2.0, cy=H / 2.0):
        return cls(p[0:3], p[3], p[4], p[5], p[6], cx, cy, None, p[7])

    # --- lens
    def distort(self, uv):
        uv = np.asarray(uv, float)
        c = np.array([self.cx, self.cy])
        if self.brown is not None:
            k1, k2 = self.brown
            x = (uv - c) / self.f
            r2 = (x * x).sum(-1, keepdims=True)
            return c + x * (1 + k1 * r2 + k2 * r2 * r2) * self.f
        if self.lam != 0.0:
            x = (uv - c) / HD
            r2 = (x * x).sum(-1, keepdims=True)
            return c + x * (2.0 / (1.0 + np.sqrt(np.maximum(1 - 4 * self.lam * r2, 1e-12)))) * HD
        return uv

    def undistort(self, uv):
        uv = np.asarray(uv, float)
        c = np.array([self.cx, self.cy])
        if self.brown is not None:
            k1, k2 = self.brown
            xd = (uv - c) / self.f
            x = xd.copy()
            for _ in range(15):
                r2 = (x * x).sum(-1, keepdims=True)
                x = xd / (1 + k1 * r2 + k2 * r2 * r2)
            return c + x * self.f
        if self.lam != 0.0:
            x = (uv - c) / HD
            r2 = (x * x).sum(-1, keepdims=True)
            return c + x / (1 + self.lam * r2) * HD
        return uv

    # --- projection
    def to_undist(self, X):
        Xc = (np.atleast_2d(np.asarray(X, float)) - self.C) @ self.R.T
        z = Xc[:, 2]
        return np.column_stack([self.cx + self.f * Xc[:, 0] / z,
                                self.cy + self.f * Xc[:, 1] / z]), z

    def project(self, X):
        uv, _ = self.to_undist(X)
        return self.distort(uv)

    def project_ground(self, xy):
        xy = np.atleast_2d(np.asarray(xy, float))
        return self.project(np.column_stack([xy, np.zeros(len(xy))]))

    def rays(self, uv):
        u = self.undistort(uv)
        dc = np.column_stack([(u[:, 0] - self.cx) / self.f,
                              (u[:, 1] - self.cy) / self.f, np.ones(len(u))])
        return dc @ self.R

    def ground(self, uv):
        d = self.rays(np.atleast_2d(uv))
        with np.errstate(divide="ignore", invalid="ignore"):
            t = -self.C[2] / d[:, 2]
        t = np.where(d[:, 2] < 0, t, np.nan)
        return self.C[None, :2] + t[:, None] * d[:, :2]

    def homography(self):
        K = np.array([[self.f, 0, self.cx], [0, self.f, self.cy], [0, 0, 1.0]])
        return K @ np.column_stack([self.R[:, 0], self.R[:, 1], -self.R @ self.C])


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


def codec_mean(frames, workdir):
    """Encode with REAL ffmpeg libx265 (1080p60, 16 Mbps, main), decode, and
    return the mean decoded luma plus the achieved bitrate."""
    fn = Path(workdir) / "clip.hevc"
    uvb = np.full((H // 2) * (W // 2) * 2, 128, np.uint8).tobytes()
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "yuv420p",
         "-s", f"{W}x{H}", "-r", str(X265["fps"]), "-i", "-", "-c:v", "libx265",
         "-profile:v", X265["profile"], "-preset", X265["preset"], "-b:v", X265["bitrate"],
         "-x265-params", (f"keyint={X265['keyint']}:min-keyint={X265['keyint']}:"
                          f"vbv-maxrate={X265['vbv_maxrate_kbps']}:"
                          f"vbv-bufsize={X265['vbv_bufsize_kbps']}:log-level=error"),
         "-pix_fmt", "yuv420p", str(fn)], stdin=subprocess.PIPE)
    nf = 0
    for fr in frames:
        enc.stdin.write(fr.tobytes())
        enc.stdin.write(uvb)
        nf += 1
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError("x265 encode failed")
    kbps = fn.stat().st_size * 8 / (nf / X265["fps"]) / 1000.0
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


# ---------------------------------------------------------------- seed ------
def _dlt(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.asarray(A, float))
    return vt[-1].reshape(3, 3)


def _angles_from_R(R):
    right, up, fwd = R[0], -R[1], R[2]
    pitch = math.asin(float(np.clip(-fwd[2], -1, 1)))
    yaw = math.atan2(fwd[0], fwd[1])
    fwd0 = np.array([math.sin(yaw), math.cos(yaw), 0.0])
    right0 = np.array([math.cos(yaw), -math.sin(yaw), 0.0])
    up_p = math.sin(pitch) * fwd0 + math.cos(pitch) * np.array([0, 0, 1.0])
    roll = math.atan2(float(right @ up_p), float(right @ right0))
    return yaw, pitch, roll


def seed_camera(corners_px, cx=W / 2.0, cy=H / 2.0):
    """Camera from the four rough corners ONLY (the first guess): closed-form focal length from the
    homography (known centred principal point, square pixels), pose from
    K^-1 H, then a 7-parameter refinement on the four corners (no lens)."""
    names = list(CORNERS)
    g = np.array([CT.LANDMARKS[n] for n in names], float)
    px = np.array([corners_px[n] for n in names], float)
    Hm = _dlt(g, px - [cx, cy])
    Hm /= np.linalg.norm(Hm[:, 0])
    h = Hm
    f0 = 1000.0
    eqs = [((h[0, 0] * h[0, 1] + h[1, 0] * h[1, 1]) / f0 ** 2, h[2, 0] * h[2, 1]),
           ((h[0, 0] ** 2 + h[1, 0] ** 2 - h[0, 1] ** 2 - h[1, 1] ** 2) / f0 ** 2,
            h[2, 0] ** 2 - h[2, 1] ** 2)]
    A = np.array([e[0] for e in eqs])
    B = np.array([e[1] for e in eqs])
    v = -(A @ B) / (A @ A) if A @ A > 0 else -1
    fmin = (W / 2) / math.tan(math.radians(65))
    fmax = (W / 2) / math.tan(math.radians(30))
    f = f0 / math.sqrt(v) if v > 0 else (W / 2) / math.tan(math.radians(45))
    f = float(np.clip(f, fmin, fmax))
    M = np.diag([1 / f, 1 / f, 1.0]) @ Hm
    s = (np.linalg.norm(M[:, 0]) + np.linalg.norm(M[:, 1])) / 2
    r1 = M[:, 0] / np.linalg.norm(M[:, 0])
    r2 = M[:, 1] - (r1 @ M[:, 1]) * r1
    r2 /= np.linalg.norm(r2)
    t = M[:, 2] / s
    ctr = np.array([CT.X_CENTER, CT.NET_Y])
    if (ctr[0] * r1 + ctr[1] * r2 + t)[2] < 0:
        r1, r2, t = -r1, -r2, -t
    R = np.column_stack([r1, r2, np.cross(r1, r2)])
    Cw = -R.T @ t
    if Cw[2] < 0:            # mirrored solution: reflect through the ground plane
        Cw = Cw * np.array([1, 1, -1])
        Cw[2] = abs(Cw[2])
    yaw, pitch, roll = _angles_from_R(R)
    p0 = np.array([*Cw, yaw, pitch, roll, f])

    def res(p):
        cam = Camera(p[0:3], p[3], p[4], p[5], p[6], cx, cy)
        uv, z = cam.to_undist(np.column_stack([g, np.zeros(4)]))
        return np.concatenate([(uv - px).ravel(), 100 * np.minimum(z, 0)])
    lo = [-50, -80, 0.2, -math.pi, -1.4, -math.pi, fmin * 0.9, ]
    hi = [60, 40, 60, math.pi, 1.4, math.pi, fmax * 1.1]
    p0 = np.clip(p0, np.array(lo) + 1e-6, np.array(hi) - 1e-6)
    sol = optimize.least_squares(res, p0, bounds=(lo, hi), x_scale="jac", max_nfev=400)
    return Camera(sol.x[0:3], *sol.x[3:7], cx, cy)


# -------------------------------------------------------------- profile -----
# A line's cross-section, as the camera integrates it: the scene along the
# image normal, blurred by a Gaussian PSF AND by the pixel's own footprint
# (a unit square projected on the normal = two boxes of widths |n_x|, |n_y|).
# _F is that blurred UNIT STEP in closed form (second antiderivative of Phi).
PHI = ndtr


def _pdf(x):
    return np.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _P1(z):
    return z * PHI(z) + _pdf(z)


def _P2(z):
    return 0.5 * ((z * z + 1) * PHI(z) + z * _pdf(z))


def _G(x, sig, b1, b2):
    h1, h2 = b1 / 2.0, b2 / 2.0
    out = (_P2((x + h1 + h2) / sig) - _P2((x + h1 - h2) / sig)
           - _P2((x - h1 + h2) / sig) + _P2((x - h1 - h2) / sig))
    return out * sig * sig / (b1 * b2)


def _Gd(x, sig, b1, b2):
    h1, h2 = b1 / 2.0, b2 / 2.0
    out = (_P1((x + h1 + h2) / sig) - _P1((x + h1 - h2) / sig)
           - _P1((x - h1 + h2) / sig) + _P1((x - h1 - h2) / sig))
    return out * sig / (b1 * b2)


def _F(x, sig, b1, b2):
    """Blurred unit step (0 -> 1 across x = 0). Evaluated on the negative side
    only, where the closed form has no cancellation."""
    neg = x <= 0
    ax = -np.abs(x)
    g = _G(ax, sig, b1, b2)
    return np.where(neg, g, 1.0 - g)


def _Fd(x, sig, b1, b2):
    return _Gd(-np.abs(x), sig, b1, b2)


def _design(d, edges, outer, sig, b1, b2, mode, kappa, nuis, deriv):
    """Columns of the linear model at offset d = s - c, and their d/dc.
    mode: 'free'  -> [1, box]              (internal line: amplitude free)
          'step'  -> [1, box, step]        (boundary line, kappa unknown)
          'kappa' -> [1, kappa*box + step] (boundary line; paint/step ratio fixed)
    nuis: extra c-independent columns (the net tape), or None.
    edges = (elo, ehi): the paint's two projected edges relative to the station
    point along +n (perspective makes them asymmetric about it)."""
    elo, ehi = edges
    box = _F(d - elo, sig, b1, b2) - _F(d - ehi, sig, b1, b2)
    cols, dcols = [np.ones_like(d)], [None]
    if deriv:
        dbox = -(_Fd(d - elo, sig, b1, b2) - _Fd(d - ehi, sig, b1, b2))
    if mode == "free":
        cols.append(box)
        dcols.append(dbox if deriv else None)
    else:
        # oriented so the COURT (surface) side is 1 whichever side run-off is on,
        # which makes kappa = paint / (surface - run-off) one number for all lines
        eo = ehi if outer > 0 else elo
        e = _F(-outer * (d - eo), sig, b1, b2)
        de = outer * _Fd(-outer * (d - eo), sig, b1, b2) if deriv else None
        if mode == "step":
            cols += [box, e]
            dcols += [dbox if deriv else None, de]
        else:
            cols.append(kappa * box + e)
            dcols.append(kappa * dbox + de if deriv else None)
    if nuis is not None:
        for col in nuis:
            cols.append(col)
            dcols.append(None)
    return cols, dcols


def _paint_amp(beta, mode, kappa):
    return beta[:, 1] * (kappa if mode == "kappa" else 1.0)


def _solve_station(st, nst, cols, y, wt):
    k = len(cols)
    G = np.empty((nst, k, k))
    r = np.empty((nst, k))
    for i in range(k):
        r[:, i] = np.bincount(st, wt * cols[i] * y, nst)
        for j in range(i, k):
            G[:, i, j] = G[:, j, i] = np.bincount(st, wt * cols[i] * cols[j], nst)
    G += np.eye(k)[None] * 1e-9
    beta = np.linalg.solve(G, r[..., None])[..., 0]
    return G, r, beta


class Profiles:
    """Pixels (or s-bins) of every kept station of one line, plus the
    per-pixel model geometry."""

    def __init__(self, st, s, y, wt, nst, edges, b1, b2, outer, win, nuis):
        self.st, self.s, self.y, self.wt, self.nst = st, s, y, wt, nst
        self.edges, self.b1, self.b2 = edges, b1, b2   # per PIXEL
        self.outer, self.win, self.nuis = outer, win, nuis


def scan_profiles(P, sig, mode, kappa, step):
    """Grid search of the paint-centre offset c per station; linear
    photometric parameters solved at every candidate."""
    st, nst, y, wt = P.st, P.nst, P.y, P.wt
    Syy = np.bincount(st, wt * y * y, nst)
    Sw = np.bincount(st, wt, nst)
    Sy = np.bincount(st, wt * y, nst)
    sse0 = Syy - Sy * Sy / np.maximum(Sw, 1e-12)
    best = np.full(nst, np.inf)
    bc = np.zeros(nst)
    wmax = float(P.win.max()) if nst else 0.0
    cands = np.arange(-math.floor(wmax / step) * step, wmax + 1e-9, step)
    for c in cands:
        cols, _ = _design(P.s - c, P.edges, P.outer, sig, P.b1, P.b2, mode, kappa, P.nuis, False)
        _, r, beta = _solve_station(st, nst, cols, y, wt)
        sse = Syy - (beta * r).sum(1)
        good = (abs(c) <= P.win + 1e-9) & (_paint_amp(beta, mode, kappa) > 0)
        sse = np.where(good, sse, np.inf)
        upd = sse < best
        best[upd] = sse[upd]
        bc[upd] = c
    return bc, best, sse0, Sw


def refine_profiles(P, sig, mode, kappa, c0, iters=6):
    """Variable-projection Gauss-Newton on each station's centre offset."""
    st, nst, y, wt = P.st, P.nst, P.y, P.wt
    c = c0.copy()
    for it in range(iters + 1):
        cols, dcols = _design(P.s - c[st], P.edges, P.outer, sig, P.b1, P.b2, mode, kappa,
                              P.nuis, True)
        G, r, beta = _solve_station(st, nst, cols, y, wt)
        model = sum(beta[st, i] * cols[i] for i in range(len(cols)))
        resid = y - model
        jc = sum(beta[st, i] * dcols[i] for i in range(len(cols)) if dcols[i] is not None)
        AtJ = np.stack([np.bincount(st, wt * col * jc, nst) for col in cols], 1)
        gam = np.linalg.solve(G, AtJ[..., None])[..., 0]
        JtJ = np.bincount(st, wt * jc * jc, nst) - (AtJ * gam).sum(1)
        Jtr = np.bincount(st, wt * jc * resid, nst)
        if it == iters:
            break
        stepc = np.clip(Jtr / np.maximum(JtJ, 1e-12), -0.3, 0.3)
        c = np.clip(c + stepc, -P.win, P.win)
    sse = np.bincount(st, wt * resid * resid, nst)
    npts = np.bincount(st, wt, nst)
    dof = np.maximum(npts - len(cols) - 1, 1)
    s2 = sse / dof
    sig_c = np.sqrt(s2 / np.maximum(JtJ, 1e-12))
    return c, sig_c, beta, sse, s2


# ---------------------------------------------------------------- fitter ----
class FitConfig:
    """R1 internals. FROZEN for scored runs; the stamp records every value."""
    passes = (
        # (lines in play, window px, mode, station spacing px, loss, f_scale, free lam)
        ("near", 40.0, "coarse", 12.0, "cauchy", 2.0, False),
        ("near", 16.0, "coarse", 10.0, "cauchy", 1.0, False),
        ("mid", 10.0, "coarse", 8.0, "cauchy", 1.0, True),
        ("all", 5.0, "fine", 4.0, "huber", 3.0, True),
        ("all", 3.0, "fine", 4.0, "huber", 3.0, True),
        ("all", 1.5, "fine", 4.0, "huber", 3.0, True),
    )
    fit_half_extra = 3.5        # fit pixels within w/2 + this * max(1, sigma) of the centre
    coarse_bin = 0.5
    coarse_step = 0.5
    fine_step = 0.1
    sig_init = 1.2
    sig_grid = tuple(float(x) for x in np.round(np.arange(0.5, 2.51, 0.05), 3))
    kappa_min_step_dn = 3.0     # below this run-off/surface step, boundary lines go 'free'
    min_dsse = 25.0             # significance, in units of the residual variance
    max_sig_c = 0.5
    sig_c_floor = 0.01
    cross_angle_deg = 10.0      # features steeper than this are crossing-tested
    parallel_angle_deg = 30.0   # features shallower than this cap the search window
    blur_reach = 3.0            # crossing exclusions extend this many PSF sigmas
    assign_frac = 0.45
    min_half_stations = 4
    tape_window_min = 4.0
    tape_poly_deg = 4

    @classmethod
    def as_dict(cls):
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(cls).items()
                if not k.startswith("_") and not callable(v) and not isinstance(v, classmethod)}


class TapeLine:
    """The net tape as the fitter models it: regulation heights (1.07 m at the
    posts, 0.914 m at the centre), 5 cm band, mesh veil below. Used ONLY as a
    measured confuser; it never enters the camera fit."""
    name, kind, width, ref_off, outer = "net_tape", "tape", TAPE_H, 0.0, -1
    n3 = np.array([0.0, 0.0, 1.0])
    x0, x1 = POST_X[0] + 0.15, POST_X[1] - 0.15

    def pts3(self, t):
        x = self.x0 + np.asarray(t, float) * (self.x1 - self.x0)
        return np.column_stack([x, np.full_like(x, NET_Y), tape_top(x) - TAPE_H / 2])


def _ground_pts3(L, t):
    t = np.asarray(t, float)[:, None]
    g = (1 - t) * L.a + t * L.b
    return np.column_stack([g, np.zeros(len(g))])


def _pts3(L, t):
    return L.pts3(t) if getattr(L, "kind", "ground") == "tape" else _ground_pts3(L, t)


def _n3(L):
    return L.n3 if getattr(L, "kind", "ground") == "tape" else np.append(L.n, 0.0)


def _in_play(line, which):
    if which == "all":
        return (0.0, 1.0)
    near_only = which == "near"
    if line.name in ("near_baseline", "near_service"):
        return (0.0, 1.0)
    if line.name in ("far_baseline", "far_service"):
        return None
    if line.name == "centre_service":
        tn = (NET_Y - line.a[1]) / (line.b[1] - line.a[1])
        return (0.0, tn - 0.5 / (line.b[1] - line.a[1])) if near_only else (0.0, 1.0)
    tn = (NET_Y - 0.5) / (line.b[1] - line.a[1])       # sidelines: a at y=0
    return (0.0, tn) if near_only else (0.0, 1.0)


def _visible_poly(cam, P3):
    uv, z = cam.to_undist(P3)
    if not (z > 0.05).all():
        return None
    return cam.distort(uv)


def _features(cam, lines, marks):
    """Every predicted feature the fitter knows about: dicts with id, image
    polyline, half width (px) and whether it is MODELLED in profiles."""
    feats = []
    for i, L in enumerate(lines):
        P = _visible_poly(cam, _ground_pts3(L, np.linspace(0, 1, 300)))
        if P is None:
            continue
        mid = (L.a + L.b) / 2
        hw = float(np.linalg.norm(cam.project_ground([mid + L.n * L.width / 2]) -
                                  cam.project_ground([mid - L.n * L.width / 2]))) / 2 + 1.0
        feats.append({"id": ("line", i), "P": P, "hw": hw, "modelled": False, "paint": True})
    for j, (x0, x1, y0, y1) in enumerate(marks):
        xm = (x0 + x1) / 2
        g = np.column_stack([np.full(20, xm), np.linspace(y0, y1, 20), np.zeros(20)])
        P = _visible_poly(cam, g)
        if P is not None:
            feats.append({"id": ("mark", j), "P": P, "hw": 2.0, "modelled": False, "paint": True})
    T = TapeLine()
    tp = T.pts3(np.linspace(0, 1, 300))
    P = _visible_poly(cam, tp)
    if P is not None:
        hw = float(np.max(np.abs(cam.project(tp + [0, 0, TAPE_H / 2])[:, 1] -
                                  cam.project(tp - [0, 0, TAPE_H / 2])[:, 1]))) / 2 + 1.0
        feats.append({"id": ("tape", 0), "P": P, "hw": hw, "modelled": True, "paint": False})
    xs = np.linspace(POST_X[0], POST_X[1], 300)
    P = _visible_poly(cam, np.column_stack([xs, np.full_like(xs, NET_Y), np.zeros_like(xs)]))
    if P is not None:
        feats.append({"id": ("netbase", 0), "P": P, "hw": 1.5, "modelled": False, "paint": False})
    for k, px in enumerate(POST_X):
        pp = np.column_stack([np.full(20, px), np.full(20, NET_Y), np.linspace(0, 1.12, 20)])
        P = _visible_poly(cam, pp)
        if P is not None:
            wpx = np.linalg.norm(cam.project([[px + POST_HALF, NET_Y, 0.5]]) -
                                 cam.project([[px - POST_HALF, NET_Y, 0.5]]))
            feats.append({"id": ("post", k), "P": P, "hw": float(wpx) / 2 + 1.0,
                          "modelled": False, "paint": False})
    return feats


def _line_hit(q, dvec, P):
    """For each station (q, dvec): the signed parameter along dvec of the
    nearest crossing with polyline P, and that segment's unit direction."""
    a = P[:-1]
    e = P[1:] - P[:-1]
    den = dvec[:, None, 0] * e[None, :, 1] - dvec[:, None, 1] * e[None, :, 0]
    w = a[None] - q[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        s = (w[..., 0] * e[None, :, 1] - w[..., 1] * e[None, :, 0]) / den
        u = (w[..., 0] * dvec[:, None, 1] - w[..., 1] * dvec[:, None, 0]) / den
    ok = (u >= 0) & (u <= 1) & np.isfinite(s)
    absS = np.where(ok, np.abs(s), np.inf)
    k = np.argmin(absS, 1)
    r = np.arange(len(q))
    sbest = np.where(ok[r, k], s[r, k], np.nan)
    ed = e[k]
    ed = ed / np.maximum(np.linalg.norm(ed, axis=1, keepdims=True), 1e-12)
    return sbest, ed


class Stations:
    pass


def make_stations(cam, L, self_id, trange, spacing, W_px, sig, feats, cfg):
    """Stations along line L, their image geometry, and the search window
    after the assignment rule (parallel neighbours) and exclusions (crossings)."""
    t = np.linspace(trange[0], trange[1], 2000)
    P3 = _pts3(L, t)
    q = _visible_poly(cam, P3)
    if q is None:
        return None
    arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))])
    if arc[-1] < 2 * spacing:
        return None
    sa = np.arange(spacing / 2, arc[-1] - spacing / 2 + 1e-9, spacing)
    ts = np.interp(sa, arc, t)
    G3 = _pts3(L, ts)
    qs = cam.project(G3)
    dt = 1e-4
    tan = cam.project(_pts3(L, np.minimum(ts + dt, 1.0))) - cam.project(_pts3(L, np.maximum(ts - dt, 0.0)))
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    nrm = np.column_stack([-tan[:, 1], tan[:, 0]])
    n3 = _n3(L)
    gn = cam.project(G3 + n3 * 1e-3) - qs
    nrm *= np.sign((nrm * gn).sum(1))[:, None]
    # each paint edge's image line, intersected with the station's normal (the
    # edges converge in perspective, so a point-to-normal projection is biased)
    G3b = _pts3(L, np.where(ts + 1e-3 <= 1.0, ts + 1e-3, ts - 1e-3))
    ecross = []
    for sgn_e in (1.0, -1.0):
        A = cam.project(G3 + sgn_e * n3 * L.width / 2)
        Bq = cam.project(G3b + sgn_e * n3 * L.width / 2)
        dv = Bq - A
        dv /= np.linalg.norm(dv, axis=1, keepdims=True)
        num = (A - qs)[:, 0] * dv[:, 1] - (A - qs)[:, 1] * dv[:, 0]
        den = nrm[:, 0] * dv[:, 1] - nrm[:, 1] * dv[:, 0]
        ecross.append(num / den)
    ea, eb = ecross
    elo, ehi = np.minimum(ea, eb), np.maximum(ea, eb)
    ww = ehi - elo
    fh = np.maximum(np.abs(elo), np.abs(ehi)) + cfg.fit_half_extra * max(1.0, sig)
    win = np.full(len(qs), W_px, float)
    keep = (qs[:, 0] > 2) & (qs[:, 0] < W - 3) & (qs[:, 1] > 2) & (qs[:, 1] < H - 3)
    cosx = math.cos(math.radians(cfg.cross_angle_deg))
    cosp = math.cos(math.radians(cfg.parallel_angle_deg))
    is_tape = getattr(L, "kind", "ground") == "tape"
    near_tape = np.full(len(qs), False)
    for F in feats:
        if F["id"] == self_id:
            continue
        P, hw = F["P"], F["hw"]
        sn, en = _line_hit(qs, nrm, P)
        par = np.isfinite(sn) & (np.abs((en * tan).sum(1)) >= cosp)
        if not (is_tape and F["paint"]):
            if F["modelled"]:
                cap = cfg.assign_frac * np.abs(sn)
                near_tape |= par & (np.abs(sn) - hw < W_px + fh + 2.0 * sig + 2.0)
            else:
                cap = np.minimum(cfg.assign_frac * np.abs(sn), np.abs(sn) - hw - fh - 1.0)
            win = np.where(par, np.minimum(win, cap), win)
        if F["id"][0] == "mark":
            # a centre mark can be shorter than a pixel: exclude by distance
            ctr = P.mean(0)
            ext = float(np.max(np.abs((P - ctr) @ tan.T)))
            dal = np.abs(((ctr - qs) * tan).sum(1))
            dno = np.abs(((ctr - qs) * nrm).sum(1))
            keep &= ~((dal < spacing / 2 + ext + hw + cfg.blur_reach * sig) &
                      (dno < win + fh + hw + cfg.blur_reach * sig))
            continue
        stt, et = _line_hit(qs, tan, P)
        cosa = np.abs((et * tan).sum(1))
        crs = np.isfinite(stt) & (cosa < cosx)
        sinang = np.sqrt(np.clip(1 - cosa ** 2, 1e-6, 1))
        reach = (spacing / 2 + (win + fh) * cosa / sinang
                 + (hw + cfg.blur_reach * sig) / sinang)
        keep &= ~(crs & (np.abs(stt) < reach))
    keep &= win >= 0.3
    S = Stations()
    S.g, S.q, S.tan, S.nrm, S.ww, S.fh, S.win = G3[:, :2], qs, tan, nrm, ww, fh, win
    S.elo, S.ehi = elo, ehi
    S.keep, S.spacing, S.near_tape = keep, spacing, near_tape
    return S


def gather_pixels(img, S, coarse, binw):
    """Pixels (or s-bins) of each kept station: (idx, st, s, y, wt)."""
    idx = np.flatnonzero(S.keep)
    if len(idx) == 0:
        return None
    q, tan, nrm = S.q[idx], S.tan[idx], S.nrm[idx]
    reach = S.win[idx] + S.fh[idx]
    half_along = S.spacing / 2
    ext = np.abs(tan) * half_along + np.abs(nrm) * reach[:, None]
    lo = np.floor(q - ext).astype(int)
    hi = np.ceil(q + ext).astype(int)
    nx = hi[:, 0] - lo[:, 0] + 1
    ny = hi[:, 1] - lo[:, 1] + 1
    cnt = nx * ny
    tot = int(cnt.sum())
    st = np.repeat(np.arange(len(idx)), cnt)
    start = np.concatenate([[0], np.cumsum(cnt)[:-1]])
    k = np.arange(tot) - np.repeat(start, cnt)
    px = lo[st, 0] + k % nx[st]
    py = lo[st, 1] + k // nx[st]
    dx = px - q[st, 0]
    dy = py - q[st, 1]
    al = dx * tan[st, 0] + dy * tan[st, 1]
    s = dx * nrm[st, 0] + dy * nrm[st, 1]
    ok = (np.abs(al) <= half_along) & (np.abs(s) <= reach[st]) & \
        (px >= 0) & (px < W) & (py >= 0) & (py < H)
    st, s = st[ok], s[ok]
    y = img[py[ok], px[ok]].astype(float)
    if coarse:
        nb = int(np.ceil(2 * reach.max() / binw)) + 2
        bi = np.floor((s + reach.max()) / binw).astype(int)
        key = st * nb + bi
        u, inv = np.unique(key, return_inverse=True)
        wsum = np.bincount(inv)
        st = (u // nb).astype(int)
        s = np.bincount(inv, s) / wsum
        y = np.bincount(inv, y) / wsum
        wt = wsum.astype(float)
    else:
        wt = np.ones_like(s)
    return idx, st, s, y, wt


def _profiles(img, S, L, sig, coarse, cfg, tape_curve=None, tape_hw=None):
    got = gather_pixels(img, S, coarse, cfg.coarse_bin)
    if got is None:
        return None, None
    idx, st, s, y, wt = got
    nb1 = np.maximum(np.abs(S.nrm[idx, 0]), 0.05)
    nb2 = np.maximum(np.abs(S.nrm[idx, 1]), 0.05)
    nuis = None
    if tape_curve is not None and not coarse and S.near_tape[idx].any():
        stp, _ = _line_hit(S.q[idx], S.nrm[idx], tape_curve)
        use = S.near_tape[idx] & np.isfinite(stp)
        stp = np.where(use, stp, 0.0)
        ps = s - stp[st]
        u = use[st].astype(float)
        b1, b2 = nb1[st], nb2[st]
        tb = (_F(ps + tape_hw, sig, b1, b2) - _F(ps - tape_hw, sig, b1, b2)) * u
        tv = _F(ps + tape_hw, sig, b1, b2) * u
        nuis = [tb, tv]
    P = Profiles(st, s, y, wt, len(idx), (S.elo[idx][st], S.ehi[idx][st]), nb1[st], nb2[st], L.outer,
                 S.win[idx], nuis)
    return P, idx


def _mode_for(L, coarse, kappa):
    if L.outer == 0:
        return "free"
    if coarse or kappa is None:
        return "step" if coarse else "free"
    return "kappa"


def measure_line(img, S, L, sig, kappa, mode_pass, cfg, tape_curve=None, tape_hw=None):
    coarse = mode_pass == "coarse"
    P, idx = _profiles(img, S, L, sig, coarse, cfg, tape_curve, tape_hw)
    if P is None:
        return None
    mode = _mode_for(L, coarse, kappa)
    step = cfg.coarse_step if coarse else cfg.fine_step
    c, sse, sse0, sw = scan_profiles(P, sig, mode, kappa, step)
    if coarse:
        s2 = sse / np.maximum(sw - 4, 1)
        sig_c = np.ones(len(c))
        beta = None
    else:
        c, sig_c, beta, sse, s2 = refine_profiles(P, sig, mode, kappa, c)
    with np.errstate(invalid="ignore", divide="ignore"):
        sigf = (sse0 - sse) / s2
    ok = np.isfinite(sse) & (sigf > cfg.min_dsse) & (np.abs(c) < P.win - 0.02)
    if not coarse:
        ok &= np.isfinite(sig_c) & (sig_c < cfg.max_sig_c) & (_paint_amp(beta, mode, kappa) > 0)
    pts = S.q[idx] + c[:, None] * S.nrm[idx]
    return {"idx": idx[ok], "pts": pts[ok], "g": S.g[idx][ok], "sig_c": sig_c[ok],
            "c": c[ok], "n_try": len(idx), "mode": mode}


def estimate_photometry(img, cam, lines, feats, cfg):
    """Global blur sigma (grid search) and the paint/step ratio kappa, both
    from the two strong NEAR lines. kappa is what makes a sub-pixel paint band
    lying ON a colour boundary separable from a shift of that boundary."""
    parts = []
    for name in ("near_baseline", "near_service"):
        li = [L.name for L in lines].index(name)
        L = lines[li]
        S = make_stations(cam, L, ("line", li), (0, 1), 4.0, 1.5, cfg.sig_init, feats, cfg)
        if S is None:
            continue
        P, idx = _profiles(img, S, L, cfg.sig_init, False, cfg)
        if P is None:
            continue
        mode = "step" if L.outer else "free"
        c0, *_ = scan_profiles(P, cfg.sig_init, mode, None, cfg.fine_step)
        parts.append((L, P, mode, c0))
    if not parts:
        return cfg.sig_init, None
    tot = []
    for sg in cfg.sig_grid:
        e = 0.0
        for L, P, mode, c0 in parts:
            c, sc, beta, sse, s2 = refine_profiles(P, sg, mode, None, c0, iters=3)
            e += float(np.nansum(sse))
        tot.append(e)
    sig = float(cfg.sig_grid[int(np.argmin(tot))])
    kappa = None
    for L, P, mode, c0 in parts:
        if mode != "step":
            continue
        c, sc, beta, sse, s2 = refine_profiles(P, sig, mode, None, c0)
        rho = beta[:, 2]
        good = np.isfinite(sc) & (sc < cfg.max_sig_c) & (np.abs(rho) > cfg.kappa_min_step_dn)
        if good.sum() >= 10 and abs(np.median(rho[good])) > cfg.kappa_min_step_dn:
            kappa = float(np.median(beta[good, 1] / rho[good]))
    return sig, kappa


def measure_tape(img, cam, feats, W_px, sig, cfg):
    """Locate the net tape (a strong, 2 px confuser) so that nearby paint
    lines can model it instead of snapping to it."""
    T = TapeLine()
    S = make_stations(cam, T, ("tape", 0), (0, 1), 4.0, max(W_px, cfg.tape_window_min), sig,
                      feats, cfg)
    tp = T.pts3(np.linspace(0, 1, 300))
    pred = _visible_poly(cam, tp)
    if pred is None:
        return None, None
    hw = float(np.median(np.abs(cam.project(tp + [0, 0, TAPE_H / 2])[:, 1] -
                                cam.project(tp - [0, 0, TAPE_H / 2])[:, 1]))) / 2
    if S is None:
        return pred, hw
    P, idx = _profiles(img, S, T, sig, False, cfg)
    if P is None:
        return pred, hw
    c0, sse, sse0, sw = scan_profiles(P, sig, "step", None, cfg.fine_step)
    c, sc, beta, sse, s2 = refine_profiles(P, sig, "step", None, c0)
    with np.errstate(invalid="ignore", divide="ignore"):
        sigf = (sse0 - sse) / s2
    ok = np.isfinite(sc) & (sc < cfg.max_sig_c) & (sigf > cfg.min_dsse) & (beta[:, 1] > 0)
    if ok.sum() < 10:
        return pred, hw
    pts = S.q[idx] + c[:, None] * S.nrm[idx]
    pts = pts[ok]
    deg = min(cfg.tape_poly_deg, int(ok.sum()) - 1)
    uc = (pts[:, 0] - W / 2) / (W / 2)
    co = np.polyfit(uc, pts[:, 1], deg)
    uu = np.linspace(pred[:, 0].min(), pred[:, 0].max(), 300)
    return np.column_stack([uu, np.polyval(co, (uu - W / 2) / (W / 2))]), hw


def _cam_residuals(p, obs, lam_free, cx, cy, lam_fixed=0.0):
    pp = np.asarray(p, float)
    if not lam_free:
        pp = np.append(pp, lam_fixed)
    cam = Camera.from_params(pp, cx, cy)
    Hm = cam.homography()
    out = []
    for L, pts, wts in obs:
        pu = cam.undistort(pts)
        ln = _hline(Hm, L.a, L.b)
        out.append(wts * (pu @ ln[:2] + ln[2]))
    _, z = cam.to_undist([[0, 0, 0], [10.97, 23.77, 0], [0, 23.77, 0], [10.97, 0, 0]])
    out.append(100.0 * np.minimum(z - 0.5, 0))        # keep the court in front
    return np.concatenate(out)


def fit_camera(cam, obs, lam_free, loss, f_scale):
    p = cam.params()
    lo = np.array([-50, -80, 0.2, -math.pi, -1.4, -math.pi, 200.0, -0.45])
    hi = np.array([60, 40, 60, math.pi, 1.4, math.pi, 4000.0, 0.45])
    if not lam_free:
        lo, hi, x0 = lo[:7], hi[:7], p[:7]
    else:
        x0 = p
    x0 = np.clip(x0, lo + 1e-9, hi - 1e-9)
    sol = optimize.least_squares(_cam_residuals, x0, bounds=(lo, hi), loss=loss,
                                 f_scale=f_scale, x_scale="jac", max_nfev=200,
                                 args=(obs, lam_free, cam.cx, cam.cy, cam.lam))
    x = sol.x if lam_free else np.append(sol.x, cam.lam)
    return Camera.from_params(x, cam.cx, cam.cy)


def r1_fit(img, seed_corners, cfg=FitConfig, cx=W / 2.0, cy=H / 2.0, trace=None):
    """The method under test. `seed_corners` is a ROUGH FIRST GUESS of the four
    doubles corners, as an automatic court detector would supply it. Returns
    the fitted camera, the final per-line measurements (distorted-pixel
    paint-centre points), the line models, sigma and kappa."""
    lines = paint_lines()
    marks = centre_marks()
    cam = seed_camera(seed_corners, cx, cy)
    sig, kappa = cfg.sig_init, None
    meas = {}
    for pi, (which, Wpx, mode, spacing, loss, fsc, lam_free) in enumerate(cfg.passes):
        feats = _features(cam, lines, marks)
        tape_curve = tape_hw = None
        if mode == "fine":
            sig, kappa = estimate_photometry(img, cam, lines, feats, cfg)
            tape_curve, tape_hw = measure_tape(img, cam, feats, Wpx, sig, cfg)
        meas = {}
        obs = []
        for li, L in enumerate(lines):
            tr = _in_play(L, which)
            if tr is None:
                continue
            S = make_stations(cam, L, ("line", li), tr, spacing, Wpx, sig, feats, cfg)
            if S is None:
                continue
            m = measure_line(img, S, L, sig, kappa, mode, cfg, tape_curve, tape_hw)
            if m is None or len(m["pts"]) < 3:
                continue
            m["n_stations"] = int(S.keep.sum())
            meas[L.name] = m
            wts = (1.0 / np.maximum(m["sig_c"], cfg.sig_c_floor) if mode == "fine"
                   else np.ones(len(m["pts"])))
            obs.append((L, m["pts"], wts))
        if not obs:
            raise RuntimeError(f"pass {pi}: no measurements")
        cam = fit_camera(cam, obs, lam_free, loss, fsc)
        if trace is not None:
            trace.append({"pass": pi, "sig": sig, "kappa": kappa,
                          "n_pts": {k: int(len(v["pts"])) for k, v in meas.items()},
                          "params": cam.params().tolist()})
    return cam, meas, lines, sig, kappa


def _hline(Hm, a, b):
    pa = Hm @ np.array([a[0], a[1], 1.0])
    pb = Hm @ np.array([b[0], b[1], 1.0])
    ln = np.cross(pa, pb)
    return ln / math.hypot(ln[0], ln[1])


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
            img, kbps = codec_mean(frames, td)
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


def stamp(arm, n, seed, workers):
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
        "codec": X265 if a["codec"] else None,
        "fitter": FitConfig.as_dict(),
        "bars": {"pass_m": BAR_M, "kill_m": KILL_M, "capture_px": 2.0},
    }


def run_arm(arm, n, seed, workers, out, verbose=True):
    from concurrent.futures import ProcessPoolExecutor
    _coverage_for(ARMS[arm])          # build/cached once, before forking workers
    tmp = OUT_DIR / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    jobs = [{"arm": arm, "trial": i, "seed": seed, "tmp": str(tmp)} for i in range(n)]
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
    res = {"stamp": stamp(arm, n, seed, workers), "summary": summ, "rows": rows}
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
    args = ap.parse_args()
    out = args.out or str(OUT_DIR / f"{args.arm}_seed{args.seed}_n{args.n}.json")
    res = run_arm(args.arm, args.n, args.seed, args.workers, out)
    print_summary(res["summary"])
    print("wrote", out)


if __name__ == "__main__":
    main()
