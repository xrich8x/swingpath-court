"""The whole-court camera fit to the PAINTED LINES (route R1) - the court's final camera.

A court pinned by a handful of points (four tapped corners, or keypoints from a
detector) misplaces the far lines by metres unless those points are right to
~0.1 px (P8 C1, docs/evidence/court-map-ceiling.md). This fit uses the points
only as a SEED: it measures every painted line to sub-pixel precision in a
narrow band around the seeded projection and solves ONE camera (position,
orientation, focal length, one division lens coefficient) that explains all of
them under the regulation dimensions.

Lifted from tools/court_fit_cp1.py (CP1 stage 1, frozen at 4ac52fc, PASS
QUALIFIED by qa). The only changes: the image size is a parameter instead of a
1920x1080 module constant, the fit can start from a Camera, and a pose-only
mode holds focal length and lens (for tracking). CP1 now imports this module;
its outputs are unchanged (tests/test_paintfit_lift.py, docs/STATE.md).

What pins the court (rule 5): measured paint positions + the regulation doubles
court (ITF, positions to the OUTSIDE of lines, 5 cm paint) + a flat court + a
known, centred principal point + one paint/step ratio and one blur measured on
the near lines. Measured on synthetic courts only (docs/evidence/court-fit-cp1.md).

Camera convention: court metres (x across, y along, z up; swingvision.court).
`Camera.R` rows are (right, down, forward), so x_cam = R @ (X - C) - the OpenCV
convention with rvec = Rodrigues(R), tvec = -R @ C.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import optimize
from scipy.special import ndtr

from . import court as CT

CORNERS = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")

# ------------------------------------------------------ regulation paint -----
PAINT_W = 0.05                  # ITF line width (baselines may be up to 10 cm)
NET_Y = CT.NET_Y
POST_X = (CT.X_LEFT_POST, CT.X_RIGHT_POST)
NET_XM = (POST_X[0] + POST_X[1]) / 2.0
TAPE_H = 0.05
POST_HALF = 0.05


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



# --------------------------------------------------------------- camera -----
class Camera:
    """Pinhole camera in swingvision court metres (x width, y length, z up).
    yaw/pitch/roll follow C1's true_projector (pitch = tilt down). Lens is
    either Brown (k1, k2) in f-normalised coords, or division `lam` in
    HD-normalised coords, or none. `wh` is the image size: HD, the division
    model's radius normaliser, is half its diagonal."""

    def __init__(self, C, yaw, pitch, roll, f, cx, cy,
                 brown=None, lam=0.0, *, wh):
        self.wh = (wh[0], wh[1])
        self.hd = math.hypot(wh[0] / 2.0, wh[1] / 2.0)
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
    def from_params(cls, p, cx, cy, *, wh):
        return cls(p[0:3], p[3], p[4], p[5], p[6], cx, cy, None, p[7], wh=wh)

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
            x = (uv - c) / self.hd
            r2 = (x * x).sum(-1, keepdims=True)
            return c + x * (2.0 / (1.0 + np.sqrt(np.maximum(1 - 4 * self.lam * r2, 1e-12)))) * self.hd
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
            x = (uv - c) / self.hd
            r2 = (x * x).sum(-1, keepdims=True)
            return c + x / (1 + self.lam * r2) * self.hd
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


def seed_camera(corners_px, cx, cy, wh):
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
    W = wh[0]
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
        cam = Camera(p[0:3], p[3], p[4], p[5], p[6], cx, cy, wh=wh)
        uv, z = cam.to_undist(np.column_stack([g, np.zeros(4)]))
        return np.concatenate([(uv - px).ravel(), 100 * np.minimum(z, 0)])
    lo = [-50, -80, 0.2, -math.pi, -1.4, -math.pi, fmin * 0.9, ]
    hi = [60, 40, 60, math.pi, 1.4, math.pi, fmax * 1.1]
    p0 = np.clip(p0, np.array(lo) + 1e-6, np.array(hi) - 1e-6)
    sol = optimize.least_squares(res, p0, bounds=(lo, hi), x_scale="jac", max_nfev=400)
    return Camera(sol.x[0:3], *sol.x[3:7], cx, cy, wh=wh)


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
    W, H = cam.wh
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
    H, W = img.shape[:2]
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
    W = cam.wh[0]
    uc = (pts[:, 0] - W / 2) / (W / 2)
    co = np.polyfit(uc, pts[:, 1], deg)
    uu = np.linspace(pred[:, 0].min(), pred[:, 0].max(), 300)
    return np.column_stack([uu, np.polyval(co, (uu - W / 2) / (W / 2))]), hw


def _cam_residuals(p, obs, lam_free, cx, cy, lam_fixed=0.0, wh=None, fixed=None):
    pp = np.asarray(p, float)
    if fixed is not None:                 # pose-only: (f, lam) held
        pp = np.append(pp, fixed)
    elif not lam_free:
        pp = np.append(pp, lam_fixed)
    cam = Camera.from_params(pp, cx, cy, wh=wh)
    Hm = cam.homography()
    out = []
    for L, pts, wts in obs:
        pu = cam.undistort(pts)
        ln = _hline(Hm, L.a, L.b)
        out.append(wts * (pu @ ln[:2] + ln[2]))
    _, z = cam.to_undist([[0, 0, 0], [10.97, 23.77, 0], [0, 23.77, 0], [10.97, 0, 0]])
    out.append(100.0 * np.minimum(z - 0.5, 0))        # keep the court in front
    return np.concatenate(out)


def fit_camera(cam, obs, lam_free, loss, f_scale, pose_only=False):
    """One robust least-squares camera solve on the measured paint points.
    pose_only holds focal length and lens at `cam`'s values (tracking a
    fixed-zoom phone: only position and orientation move)."""
    p = cam.params()
    if pose_only:
        lo = np.array([-50, -80, 0.2, -math.pi, -1.4, -math.pi])
        hi = np.array([60, 40, 60, math.pi, 1.4, math.pi])
        x0 = np.clip(p[:6], lo + 1e-9, hi - 1e-9)
        sol = optimize.least_squares(_cam_residuals, x0, bounds=(lo, hi), loss=loss,
                                     f_scale=f_scale, x_scale="jac", max_nfev=200,
                                     args=(obs, False, cam.cx, cam.cy, cam.lam, cam.wh,
                                           p[6:8]))
        return Camera.from_params(np.append(sol.x, p[6:8]), cam.cx, cam.cy, wh=cam.wh)
    lo = np.array([-50, -80, 0.2, -math.pi, -1.4, -math.pi, 200.0, -0.45])
    hi = np.array([60, 40, 60, math.pi, 1.4, math.pi, 4000.0, 0.45])
    if not lam_free:
        lo, hi, x0 = lo[:7], hi[:7], p[:7]
    else:
        x0 = p
    x0 = np.clip(x0, lo + 1e-9, hi - 1e-9)
    sol = optimize.least_squares(_cam_residuals, x0, bounds=(lo, hi), loss=loss,
                                 f_scale=f_scale, x_scale="jac", max_nfev=200,
                                 args=(obs, lam_free, cam.cx, cam.cy, cam.lam, cam.wh))
    x = sol.x if lam_free else np.append(sol.x, cam.lam)
    return Camera.from_params(x, cam.cx, cam.cy, wh=cam.wh)


def r1_fit(img, seed_corners, cfg=FitConfig, cx=None, cy=None, trace=None, *,
           seed_cam=None, pose_only=False):
    """The R1 fit. `seed_corners` is a ROUGH FIRST GUESS of the four doubles
    corners, as an automatic court detector would supply it; or pass
    `seed_cam` (a Camera, e.g. from a keypoint PnP solve) instead. `img` is one
    grey image (a static window of frames averaged). The principal point
    defaults to the image centre and is never fitted. Returns the fitted
    camera, the final per-line measurements (distorted-pixel paint-centre
    points), the line models, sigma and kappa."""
    wh = (img.shape[1], img.shape[0])
    cx = wh[0] / 2.0 if cx is None else cx
    cy = wh[1] / 2.0 if cy is None else cy
    lines = paint_lines()
    marks = centre_marks()
    if seed_cam is not None:
        p = seed_cam.params()
        cam = Camera(p[0:3], p[3], p[4], p[5], p[6], cx, cy, None, p[7], wh=wh)
    else:
        cam = seed_camera(seed_corners, cx, cy, wh)
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
        cam = fit_camera(cam, obs, lam_free, loss, fsc, pose_only)
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
