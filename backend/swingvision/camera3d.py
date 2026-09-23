"""The court's 3D camera: intrinsics K, extrinsics (R, t), a lens model, and the
two solves that produce it.

    keypoints --solve_pnp_seed--> rough camera --fit_camera_on_paint--> the camera

The keypoint PnP solve is only a FIRST GUESS. A camera pinned by points
misplaces the far lines by metres unless each point is right to ~0.1 px (P8 C1,
docs/evidence/court-map-ceiling.md); the whole-court fit to the painted lines
(paintfit, CP1) is what places the court. Hard rule 5 applies to everything
here: `pinned_by` names what fixed each camera, and a reprojection error is a
diagnostic, never evidence that the court is right.

World frame: court metres from `court.py` - x across (left doubles sideline =
0), y along (near baseline = 0), z UP. Camera frame: OpenCV (x right, y down,
z forward), x_cam = R @ X + t. The principal point is the image centre and is
never fitted; pixels are square.

Lens models (`lens`, `dist`):
  "none"     - ()
  "division" - (lam,)   paintfit's one-parameter model, radius normalised by
                        half the image diagonal (what the paint fit solves)
  "brown"    - (k1, k2) radius normalised by the focal length
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import court, paintfit

LENS_MODELS = ("none", "division", "brown")
PINNED_PNP = ("keypoint PnP: detected keypoints + regulation dimensions + "
              "centred principal point, focal from the court homography")
PINNED_PAINT = ("paint fit (R1): measured paint + regulation dimensions + flat court + "
                "centred principal point + near-line blur and paint/step ratio")


def _rot_to_rvec(R):
    import cv2
    return cv2.Rodrigues(np.asarray(R, float))[0].ravel()


def _rvec_to_rot(rvec):
    import cv2
    return cv2.Rodrigues(np.asarray(rvec, float).reshape(3, 1))[0]


@dataclass
class CourtCamera:
    f_px: float
    rvec: np.ndarray
    tvec: np.ndarray
    image_wh: tuple
    lens: str = "none"
    dist: tuple = ()
    pinned_by: str = ""
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        self.rvec = np.asarray(self.rvec, float).reshape(3)
        self.tvec = np.asarray(self.tvec, float).reshape(3)
        self.image_wh = (int(self.image_wh[0]), int(self.image_wh[1]))
        self.dist = tuple(float(v) for v in self.dist)
        if self.lens not in LENS_MODELS:
            raise ValueError(f"lens {self.lens!r} not one of {LENS_MODELS}")
        need = {"none": 0, "division": 1, "brown": 2}[self.lens]
        if len(self.dist) != need:
            raise ValueError(f"lens {self.lens!r} takes {need} coefficients, got {self.dist}")
        self._pf = None

    # --- intrinsics / extrinsics
    @property
    def cx(self) -> float:
        return self.image_wh[0] / 2.0

    @property
    def cy(self) -> float:
        return self.image_wh[1] / 2.0

    @property
    def K(self) -> np.ndarray:
        return np.array([[self.f_px, 0, self.cx], [0, self.f_px, self.cy], [0, 0, 1.0]])

    @property
    def R(self) -> np.ndarray:
        return _rvec_to_rot(self.rvec)

    def position_m(self) -> np.ndarray:
        """Camera centre in court metres (x, y, height)."""
        return -self.R.T @ self.tvec

    def hfov_deg(self) -> float:
        return math.degrees(2.0 * math.atan(self.image_wh[0] / (2.0 * self.f_px)))

    # --- the paintfit camera does the lens and ray arithmetic
    def to_paintfit(self) -> paintfit.Camera:
        if self._pf is None:
            R = self.R
            yaw, pitch, roll = paintfit._angles_from_R(R)
            brown = self.dist if self.lens == "brown" else None
            lam = self.dist[0] if self.lens == "division" else 0.0
            pf = paintfit.Camera(self.position_m(), yaw, pitch, roll, self.f_px,
                                 self.cx, self.cy, brown, lam, wh=self.image_wh)
            pf.R = R                     # exact, not re-derived from the angles
            self._pf = pf
        return self._pf

    @classmethod
    def from_paintfit(cls, cam: paintfit.Camera, pinned_by: str = PINNED_PAINT, **extra):
        if cam.brown is not None:
            lens, dist = "brown", tuple(cam.brown)
        elif cam.lam != 0.0:
            lens, dist = "division", (cam.lam,)
        else:
            lens, dist = "none", ()
        if abs(cam.cx - cam.wh[0] / 2.0) > 1e-9 or abs(cam.cy - cam.wh[1] / 2.0) > 1e-9:
            raise ValueError("CourtCamera fixes the principal point at the image centre")
        R = np.asarray(cam.R, float)
        return cls(cam.f, _rot_to_rvec(R), -R @ cam.C, cam.wh, lens, dist, pinned_by, dict(extra))

    def project(self, xyz) -> np.ndarray:
        """Court points (x, y, z metres) -> distorted image pixels. Rows behind
        the camera come back NaN (perspective is meaningless there)."""
        pf = self.to_paintfit()
        uv, z = pf.to_undist(np.atleast_2d(np.asarray(xyz, float)))
        out = pf.distort(uv)
        out[z <= 1e-6] = np.nan
        return out

    def undistort(self, uv) -> np.ndarray:
        return self.to_paintfit().undistort(np.atleast_2d(np.asarray(uv, float)))

    def ray(self, uv):
        """Pixels -> (camera centre, unit ray directions in court metres). The
        single-camera inverse projection: a point on the ray is NOT located
        until something else (a plane, a height, a physical model) pins it."""
        d = self.to_paintfit().rays(np.atleast_2d(np.asarray(uv, float)))
        return self.position_m(), d / np.linalg.norm(d, axis=1, keepdims=True)

    def ground_point(self, uv) -> np.ndarray:
        """Pixels -> court (x, y) where the ray meets z = 0; NaN above the horizon."""
        return self.to_paintfit().ground(np.atleast_2d(np.asarray(uv, float)))

    def ground_homography(self) -> np.ndarray:
        """Court plane -> UNDISTORTED pixels, K [r1 r2 t], scaled so H[2,2] = 1.
        The same as the old flat model only when `lens == "none"`; with a lens,
        undistort pixels before using it."""
        R = self.R
        H = self.K @ np.column_stack([R[:, 0], R[:, 1], self.tvec])
        return H / H[2, 2]

    def reprojection_px(self, kps_px: dict) -> dict:
        """Per-keypoint pixel residual. DIAGNOSTIC ONLY (rule 5)."""
        names = [n for n in kps_px if n in court.LANDMARKS_3D]
        if not names:
            return {}
        pred = self.project([court.LANDMARKS_3D[n] for n in names])
        obs = np.array([kps_px[n] for n in names], float)
        return {n: float(e) for n, e in zip(names, np.linalg.norm(pred - obs, axis=1))}

    # --- serialisation (match.json `setup.camera`)
    def to_dict(self) -> dict:
        pos = self.position_m()
        return {
            "model": "pinhole",
            "image_wh": list(self.image_wh),
            "f_px": float(self.f_px),
            "cx": self.cx, "cy": self.cy,
            "lens": self.lens,
            "dist": list(self.dist),
            "rvec": [float(v) for v in self.rvec],
            "tvec": [float(v) for v in self.tvec],
            "position_m": [float(v) for v in pos],
            "hfov_deg": self.hfov_deg(),
            "pinned_by": self.pinned_by,
            **{k: v for k, v in self.extra.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CourtCamera":
        known = {"model", "image_wh", "f_px", "cx", "cy", "lens", "dist", "rvec", "tvec",
                 "position_m", "hfov_deg", "pinned_by"}
        if d.get("model") != "pinhole":
            raise ValueError(f"unknown camera model {d.get('model')!r}")
        return cls(d["f_px"], d["rvec"], d["tvec"], tuple(d["image_wh"]), d.get("lens", "none"),
                   tuple(d.get("dist", ())), d.get("pinned_by", ""),
                   {k: v for k, v in d.items() if k not in known})


# ------------------------------------------------------------ PnP seed -----
@dataclass
class PnPSeed:
    camera: CourtCamera
    inliers: list
    dropped_cross_ratio: list
    rms_px: float            # over inliers; diagnostic only


def _hfov_to_f(hfov_deg, w):
    return (w / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)


def _focal_candidates(names, obj, img, wh, f_hint):
    if f_hint is not None:
        return [float(f_hint)]
    import cv2

    from . import calibration
    cands = []
    ground = [i for i, n in enumerate(names) if obj[i, 2] == 0.0]
    if len(ground) >= 4:
        Hm, _ = cv2.findHomography(obj[ground, :2], img[ground], cv2.RANSAC, 0.01 * max(wh))
        if Hm is not None:
            f = calibration.focal_from_homography(Hm, wh)
            if f is not None:
                cands.append(float(f))
    cands += [_hfov_to_f(h, wh[0]) for h in range(40, 115, 5)]
    return cands


def _pnp_at_focal(obj, img, K, thr):
    import cv2
    ok, rvec, tvec, inl = cv2.solvePnPRansac(
        obj, img, K, None, iterationsCount=300, reprojectionError=thr,
        confidence=0.999, flags=cv2.SOLVEPNP_SQPNP)
    if not ok or inl is None or len(inl) < 4:
        return None
    inl = inl.ravel()
    rvec, tvec = cv2.solvePnPRefineLM(obj[inl], img[inl], K, None, rvec, tvec)
    proj, _ = cv2.projectPoints(obj, rvec, tvec, K, None)
    err = np.linalg.norm(proj.reshape(-1, 2) - img, axis=1)
    return rvec.ravel(), tvec.ravel(), err


def _joint_refine(obj, img, wh, f, rvec, tvec, thr):
    """(rvec, tvec, f) least squares on the inliers, robust loss, principal
    point held at the centre. Focal bounded to a 20-130 deg horizontal FOV."""
    import cv2
    from scipy import optimize
    cx, cy = wh[0] / 2.0, wh[1] / 2.0

    def res(p):
        K = np.array([[p[6], 0, cx], [0, p[6], cy], [0, 0, 1.0]])
        proj, _ = cv2.projectPoints(obj, p[:3], p[3:6], K, None)
        return (proj.reshape(-1, 2) - img).ravel()
    lo = [-np.inf] * 6 + [_hfov_to_f(130.0, wh[0])]
    hi = [np.inf] * 6 + [_hfov_to_f(20.0, wh[0])]
    x0 = np.concatenate([rvec, tvec, [np.clip(f, lo[6] * 1.0001, hi[6] * 0.9999)]])
    sol = optimize.least_squares(res, x0, bounds=(lo, hi), loss="huber",
                                 f_scale=max(thr / 3.0, 1.0), x_scale="jac", max_nfev=400)
    return sol.x[:3], sol.x[3:6], float(sol.x[6])


def solve_pnp_seed(kps, image_wh=None, f_hint: float | None = None, *,
                   thr_px: float | None = None, min_points: int = 5,
                   use_cross_ratio: bool = True) -> PnPSeed | None:
    """Rough camera from named keypoints (a `courtfit.KeypointSet` or a plain
    {name: (u, v)} dict) under the regulation 3D court. No lens.

    Keypoints that break a line's cross-ratio are dropped first; RANSAC over
    each focal candidate (device focal `f_hint`, else the court homography's
    self-calibrated focal plus a 40-110 deg sweep) keeps the rest; the best
    candidate is refined jointly with the focal length. `thr_px` defaults to
    1% of the image width. Returns None if fewer than `min_points` usable
    points or no solve places the court in front of a camera above the ground."""
    from . import courtfit
    px = getattr(kps, "px", kps)
    wh = tuple(image_wh or getattr(kps, "image_wh", None) or ())
    if len(wh) != 2 or wh[0] <= 0:
        raise ValueError("image_wh is required")
    dropped = []
    if use_cross_ratio:
        out, _ = courtfit.cross_ratio_check(px, wh[1])
        dropped = sorted(out)
    names = [n for n in px if n in court.LANDMARKS_3D and n not in dropped]
    if len(names) < min_points:
        return None
    obj = np.array([court.LANDMARKS_3D[n] for n in names], float)
    img = np.array([px[n] for n in names], float)
    thr = thr_px if thr_px is not None else 0.01 * wh[0]

    best = None
    for f in _focal_candidates(names, obj, img, wh, f_hint):
        K = np.array([[f, 0, wh[0] / 2.0], [0, f, wh[1] / 2.0], [0, 0, 1.0]])
        got = _pnp_at_focal(obj, img, K, thr)
        if got is None:
            continue
        rvec, tvec, err = got
        R = _rvec_to_rot(rvec)
        C = -R.T @ tvec
        depth = (obj @ R.T + tvec)[:, 2]
        if C[2] <= 0 or not np.all(depth > 0):
            continue
        score = float(np.sum(np.minimum(err, thr) ** 2))       # MSAC
        if best is None or score < best[0]:
            best = (score, f, rvec, tvec)
    if best is None:
        return None
    _, f, rvec, tvec = best
    if f_hint is None:
        K = np.array([[f, 0, wh[0] / 2.0], [0, f, wh[1] / 2.0], [0, 0, 1.0]])
        inl = _pnp_at_focal(obj, img, K, thr)[2] <= thr
        rvec, tvec, f = _joint_refine(obj[inl], img[inl], wh, f, rvec, tvec, thr)
    cam = CourtCamera(f, rvec, tvec, wh, "none", (), PINNED_PNP,
                      {"seed_source": getattr(kps, "source", "keypoints")})
    err = np.linalg.norm(cam.project(obj) - img, axis=1)
    inl = err <= thr
    if cam.position_m()[2] <= 0 or inl.sum() < 4:
        return None
    return PnPSeed(cam, [n for n, k in zip(names, inl) if k], dropped,
                   float(np.sqrt(np.mean(err[inl] ** 2))))


# ------------------------------------------------------------ paint fit ----
@dataclass
class PaintFitResult:
    camera: CourtCamera
    sigma_px: float
    kappa: float | None
    n_points: dict
    meas: dict = field(default_factory=dict)


def grey_mean(frames) -> np.ndarray:
    """One float grey image from a frame or a static window of frames
    (averaging is what the paint fit was measured on)."""
    import cv2
    if isinstance(frames, np.ndarray):
        frames = [frames]
    acc, n = None, 0
    for fr in frames:
        g = fr if fr.ndim == 2 else cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        g = g.astype(float)
        acc = g if acc is None else acc + g
        n += 1
    if acc is None:
        raise ValueError("no frames")
    return acc / n


def fit_camera_on_paint(frames, seed: CourtCamera, *, pose_only: bool = False,
                        cfg=None) -> PaintFitResult:
    """THE court camera: paintfit's R1 fit started from `seed`. Focal length
    and one division coefficient are fitted unless `pose_only` (tracking a
    phone whose zoom and lens did not change), which holds both at the seed's.
    Raises if the fit cannot measure any line."""
    img = grey_mean(frames)
    wh = (img.shape[1], img.shape[0])
    if tuple(seed.image_wh) != wh:
        raise ValueError(f"seed camera is {seed.image_wh}, frames are {wh}")
    if seed.lens == "brown":
        raise ValueError("the paint fit models the lens as division; convert the seed first")
    cam, meas, _lines, sig, kappa = paintfit.r1_fit(
        img, None, cfg or paintfit.FitConfig, seed_cam=seed.to_paintfit(), pose_only=pose_only)
    n_pts = {k: int(len(v["pts"])) for k, v in meas.items()}
    out = CourtCamera.from_paintfit(
        cam, PINNED_PAINT, seed_source=seed.extra.get("seed_source", "camera"),
        paint_fit=True, paint_points=int(sum(n_pts.values())))
    return PaintFitResult(out, float(sig), kappa, n_pts, meas)


# ------------------------------------------------- paint measurements -----
def ridge_offsets(grey, pts, nrm, reach, min_dn, step=0.5):
    """Sub-pixel offset along `nrm` from each point to the nearest bright paint
    ridge within +-`reach` px, and whether one was found. The ridge is the local
    maximum of the grey profile nearest the point that stands `min_dn` above the
    profile's median; its position is refined by a parabola through 3 samples."""
    from scipy import ndimage
    s = np.arange(-reach, reach + 1e-9, step)
    xy = pts[:, None, :] + s[None, :, None] * nrm[:, None, :]
    prof = ndimage.map_coordinates(np.asarray(grey, float), [xy[..., 1].ravel(), xy[..., 0].ravel()],
                                   order=1, mode="nearest").reshape(len(pts), len(s))
    base = np.median(prof, axis=1)
    peak = np.zeros_like(prof, bool)
    peak[:, 1:-1] = (prof[:, 1:-1] >= prof[:, :-2]) & (prof[:, 1:-1] > prof[:, 2:])
    peak &= prof >= base[:, None] + min_dn
    dist = np.where(peak, np.abs(s)[None, :], np.inf)
    k = np.argmin(dist, axis=1)
    found = np.isfinite(dist[np.arange(len(pts)), k])
    k = np.clip(k, 1, len(s) - 2)
    r = np.arange(len(pts))
    y0, y1, y2 = prof[r, k - 1], prof[r, k], prof[r, k + 1]
    den = y0 - 2 * y1 + y2
    with np.errstate(divide="ignore", invalid="ignore"):
        frac = np.where(np.abs(den) > 1e-9, 0.5 * (y0 - y2) / den, 0.0)
    return s[k] + np.clip(frac, -0.5, 0.5) * step, found


def paint_samples(step_m, clear_m=0.3):
    """Points every `step_m` along the CENTRE of every painted line
    (paintfit.paint_lines: ITF positions are line edges, the paint ridge is
    its centre) and each point's line direction. Points within `clear_m` of
    another painted line are dropped: at a crossing the profile is paint on
    both sides and the ridge is meaningless. The net is not paint."""
    lines = paintfit.paint_lines()
    pts, dirs = [], []
    for L in lines:
        n = max(2, int(np.linalg.norm(L.b - L.a) / step_m))
        t = np.linspace(0.0, 1.0, n)[:, None]
        g = (1 - t) * L.a + t * L.b
        near = np.zeros(len(g), bool)
        for M in lines:
            if M is L:
                continue
            lo, hi = np.minimum(M.a, M.b), np.maximum(M.a, M.b)
            d = np.linalg.norm(g - np.clip(g, lo, hi), axis=1)     # distance to segment M
            near |= d < clear_m + M.width / 2
        g = g[~near]
        pts.append(g)
        dirs.append(np.repeat(((L.b - L.a) / np.linalg.norm(L.b - L.a))[None], len(g), 0))
    g, d = np.vstack(pts), np.vstack(dirs)
    return np.column_stack([g, np.zeros(len(g))]), np.column_stack([d, np.zeros(len(d))])


def line_normals(cam: CourtCamera, world, wdir):
    """Unit image normals (undistorted frame) of each sample's line."""
    pf = cam.to_paintfit()
    a, _ = pf.to_undist(world)
    b, _ = pf.to_undist(world + 0.05 * wdir)
    d = b - a
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
    return np.column_stack([-d[:, 1], d[:, 0]])


_SUPPORT_SAMPLES = {}


def _samples(step_m):
    """paint_samples plus, for each sample, its paintfit line index and width."""
    if step_m not in _SUPPORT_SAMPLES:
        world, wdir = paint_samples(step_m)
        lines = paintfit.paint_lines()
        ids = np.empty(len(world), int)
        for k, p in enumerate(world):
            best = None
            for i, L in enumerate(lines):
                d = L.b - L.a
                u = np.clip((p[:2] - L.a) @ d / (d @ d), 0.0, 1.0)
                e = float(np.linalg.norm(L.a + u * d - p[:2]))
                if best is None or e < best[0]:
                    best = (e, i)
            ids[k] = best[1]
        _SUPPORT_SAMPLES[step_m] = (world, wdir, ids, [L.name for L in lines],
                                    np.array([L.width for L in lines]))
    return _SUPPORT_SAMPLES[step_m]


# ------------------------------------------------- the FAR-LINE instrument -
# Why this exists: the per-point ridge finder above cannot see a line whose
# projected paint is thinner than a pixel, and at 1080p / 3 m mount / 6 m
# setback the far baseline's 5 cm of paint runs in DEPTH and projects about
# 0.14 px wide. `paint_check`'s `min_width_px_720` filter therefore DROPPED the
# far baseline and far service line on 398 of 398 G7 trials, and the tracker
# reported `locked` while those two lines were 0.57-0.70 m out (qa audit
# 2026-09-18, section 7). The contrast is still there - about 6.7 DN of peak
# against 1.8 DN of sensor noise - it is just spread too thin for ONE profile.
# So integrate ALONG the line: average the normal profiles of ~90 samples and
# the ridge stands ~9x clearer, with a peak position good to hundredths of a
# pixel. Segmented, because a camera rotated about the line's midpoint puts
# equal and opposite offsets at the two ends, which one pooled average hides.
# Pre-registered in docs/evidence/court-camera3d.md, G8.
FAR_LINES = ("far_baseline", "far_service")
# Set by G8's NOISE-ONLY development sweep on sim seeds 300-305 (1,728 cases over
# a 8 x 5 grid), scored by catch rate against incremental false-flag rate exactly
# as G4 set the cross-ratio gate. 0.75 px @720 is the registered choice: the
# highest catch among pairs costing <= 1% false flags over the good cases the
# pre-G8 check already passed (catch 0.917, false 0.000; 0.50 reaches 0.979 but
# costs 1.6%). FAR_MIN_Z was INERT across 3-8 on that sweep - it does not select
# anything - so it is left at the value the code carried before the sweep.
# NOT the 0.35 "contrast ratio" that was suggested: that number had no evidence.
FAR_TOL_PX_720 = 0.75
FAR_MIN_Z = 5.0
# The SEARCH WINDOW, and it is a corrected number. G8 registered
# "offsets s in [-reach, +reach] ... reach = 3 * far_tol" - the same 3x the
# shipped `paint_check` uses for `ridge_offsets` - and the code that ran carried
# a hard-coded `reach_px_720 = 8.0`, 3.56x wider, declared nowhere. qa found it
# on 2026-09-19 and it was not cosmetic: the net tape sits 4.8-5.6 px from the
# far service line, INSIDE the 8.0 window and OUTSIDE the registered 2.25 one,
# which is the whole of G8's BAR 4 failure. The registered coupling is restored
# here: the window is 3 x the tolerance, everywhere, and a caller that wants the
# 8.0 behaviour must ask for it by name (see G8 REMEDIATION in the evidence).
# Re-scored at this window on 2026-09-22, it is NOT a fix: on CP1's scene the
# far lines go back to `unchecked` (0 of 400 true cameras checked - the check is
# identical to the pre-G8 one on 400 of 400 trials), and on the clean sim scene
# an off-tolerance ridge falls inside the noise wing, reads as "not seen" and
# leaves the denominator, so sim seed 201's knock frame, 49 cm out, is LOCKED
# with scope `whole_court`. The 8.0 window is a separate, unregistered arm.
FAR_REACH_MULT = 3.0
FAR_REACH_PX_720 = FAR_REACH_MULT * FAR_TOL_PX_720
# OFF by default, and the reason is measured, not cautious. RE-DECIDED 2026-09-22
# at the REGISTERED window (G8 REMEDIATION): bar 1 PASS (catch 0.9028), bar 2
# PASS (0/63), bar 3 FAIL (sim seed 201's 49 cm knock frame is locked, claiming
# the whole court), bar 4 passes only VACUOUSLY (1/368 false flags because the
# far lines are never checked on that scene). The founder's pyramid arm fails
# bar 4 outright at the registered window (263/368 right cameras flagged). A
# failed gate stays failed, so this stays False.
# The ORIGINAL reason, at the unregistered 8.0 px window: G8's non-degradation
# bar was run on CP1's arm-P scene and FAILED: with the far lines checked, 369 of
# 369 RIGHT cameras are flagged - including the exact rendering camera. Isolated
# by a one-variable arm sweep to CLUTTER, not to the lens: on that scene at a 3 m
# mount and 6 m setback the NET TAPE sits 4.8-5.6 px from the far service line
# and swamps the far baseline (stacked amplitude 5.8 DN with no paint ridge -> 69
# DN of net), so the "nearest significant peak" rule locks onto the net. With no
# clutter the same instrument reads the true camera at +0.09 px, and adding LENS
# DISTORTION alone leaves it at +0.02 px. A failed gate stays failed (hard rule
# 2), so a confuser guard is a NEW experiment needing its own pre-registration.
# Until then the instrument ships measured but OFF, and `PaintCheck.scope` says
# out loud that the far lines were not verified.
# RE-DECIDED 2026-09-23 by G10 (job 2): ON, with the STEP-AWARE instrument below
# (`FAR_MODE_DEFAULT = "stepfit"`), the follow-up G10's pre-registration allowed on a
# PASS. G10 passed all five bars: held-out sim catch 72/72 with 0 false flags on
# both scenes, both known bad knock frames caught, and on CP1's cluttered scene the
# far lines checked on 99.5% of right fits with 0 new false flags (the stacked
# instrument, still available as far_mode="stack", checks them on 0%). Judged in
# the tracker by G11. Everything above is the stacked instrument's history.
FAR_LINES_DEFAULT = True
FAR_DENSE_STEP_M = 0.02
_FAR_DENSE = {}


def _far_dense(clear_m=0.3, step_m=FAR_DENSE_STEP_M):
    """Dense world centreline samples per painted line, crossings cleared."""
    key = (clear_m, step_m)
    if key not in _FAR_DENSE:
        lines = paintfit.paint_lines()
        out = []
        for L in lines:
            n = max(2, int(np.linalg.norm(L.b - L.a) / step_m))
            t = np.linspace(0.0, 1.0, n)[:, None]
            g = (1 - t) * L.a + t * L.b
            near = np.zeros(len(g), bool)
            for M in lines:
                if M is L:
                    continue
                lo, hi = np.minimum(M.a, M.b), np.maximum(M.a, M.b)
                d = np.linalg.norm(g - np.clip(g, lo, hi), axis=1)
                near |= d < clear_m + M.width / 2
            g = g[~near]
            u = (L.b - L.a) / np.linalg.norm(L.b - L.a)
            out.append((L.name, float(L.width),
                        np.column_stack([g, np.zeros(len(g))]),
                        np.repeat(np.array([u[0], u[1], 0.0])[None], len(g), 0)))
        _FAR_DENSE[key] = out
    return _FAR_DENSE[key]


def _seg_hit(s, P, tol, min_z):
    """(detected, hit, z, refined offset) for one stacked profile. The peak
    NEAREST zero that stands `min_z` robust sigmas above the profile's baseline,
    refined by the same 3-point parabola `ridge_offsets` uses. `detected` means a
    peak was found ANYWHERE in the search window; `hit` adds |offset| <= tol.

    The two are separate on purpose. A profile with no peak at all cannot tell a
    WRONG camera from paint too faint to see, and reporting that as a failed line
    would be the same dishonesty G8 exists to remove - it is reported as
    UNCHECKABLE instead (see `paint_check`).

    Deviation from G8's wording ("the largest local maximum at |s| <= tol"), made
    before any scored run and recorded in G8's results: searching the whole
    profile and testing the offset afterwards removes a boundary artefact when
    `tol` is finer than the profile step, and matches shipped `ridge_offsets`."""
    b = float(np.median(P))
    wing = np.abs(s) > tol
    if wing.sum() >= 5:
        w = P[wing]
        sd = 1.4826 * float(np.median(np.abs(w - np.median(w))))
    else:
        sd = float(np.std(P))
    sd = max(sd, 1e-6)
    pk = np.zeros(len(s), bool)
    pk[1:-1] = (P[1:-1] >= P[:-2]) & (P[1:-1] > P[2:])
    pk &= (P - b) >= min_z * sd
    if not pk.any():
        return False, False, 0.0, float("nan")
    k = int(np.flatnonzero(pk)[np.argmin(np.abs(s[np.flatnonzero(pk)]))])
    y0, y1, y2 = P[k - 1], P[k], P[k + 1]
    den = y0 - 2 * y1 + y2
    frac = 0.5 * (y0 - y2) / den if abs(den) > 1e-12 else 0.0
    off = float(s[k] + np.clip(frac, -0.5, 0.5) * (s[1] - s[0]))
    return True, bool(abs(off) <= tol), float((y1 - b) / sd), off


def far_line_stacks(grey, cam: CourtCamera, *, segments: int = 8, min_samples: int = 24,
                    step_px: float = 1.0, reach_px_720: float = FAR_REACH_PX_720,
                    prof_step_px: float = 0.25, min_width_px_720: float = 0.67,
                    clear_m: float = 0.3) -> dict:
    """{line name: (offsets_px, [stacked profile per segment], n_samples)} for the
    paint too thin for the per-point ridge finder. Split out from
    `far_line_profile` so a threshold sweep can re-score one set of measurements
    (G8) instead of re-reading the image once per threshold.

    `reach_px_720` is the search half-window and it is NOT free: G8 registered it
    as `3 * far_tol`, so a sweep over tolerances must RE-MEASURE per tolerance
    (`far_line_profile` does) rather than measure once at a wide reach and score
    narrow - a wider window can find a confuser the registered one never looks
    at. See FAR_REACH_MULT."""
    from scipy import ndimage
    g = np.asarray(grey, float)
    w, h = cam.image_wh
    s_scale = h / 720.0
    reach = reach_px_720 * s_scale
    sv = np.arange(-reach, reach + 1e-9, prof_step_px * s_scale)
    out = {}
    for name, width, world, wdir in _far_dense(clear_m):
        uv = cam.project(world)
        inb = (np.isfinite(uv).all(1) & (uv[:, 0] >= 8) & (uv[:, 0] < w - 8)
               & (uv[:, 1] >= 8) & (uv[:, 1] < h - 8))
        if inb.sum() < min_samples:
            continue
        n3 = np.column_stack([-wdir[inb, 1], wdir[inb, 0], np.zeros(int(inb.sum()))])
        half = width / 2.0
        wpx = np.linalg.norm(cam.project(world[inb] + n3 * half)
                             - cam.project(world[inb] - n3 * half), axis=1)
        thin = np.flatnonzero(inb)[wpx < min_width_px_720 * s_scale]
        if len(thin) < min_samples:
            continue
        # keep ~step_px apart in the IMAGE: oversampling correlates the noise
        pxy = uv[thin]
        d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pxy, axis=0), axis=1))]
        keep = [0]
        for i in range(1, len(d)):
            if d[i] - d[keep[-1]] >= step_px * s_scale:
                keep.append(i)
        idx = thin[np.array(keep)]
        if len(idx) < min_samples:
            continue
        nrm = line_normals(cam, world[idx], wdir[idx])
        nseg = max(1, min(segments, len(idx) // min_samples))
        bounds = np.linspace(0, len(idx), nseg + 1).astype(int)
        profs = []
        for a, b in zip(bounds[:-1], bounds[1:]):
            q, nq = uv[idx[a:b]], nrm[a:b]
            xy = q[:, None, :] + sv[None, :, None] * nq[:, None, :]
            prof = ndimage.map_coordinates(
                g, [xy[..., 1].ravel(), xy[..., 0].ravel()], order=1,
                mode="nearest").reshape(b - a, len(sv))
            profs.append(prof.mean(0))
        out[name] = (sv, profs, int(len(idx)))
    return out


def score_far_stacks(stacks, *, far_tol_px_720: float = FAR_TOL_PX_720, far_min_z: float = FAR_MIN_Z,
                     s_scale: float = 1.0, min_det_frac: float = 0.5) -> dict:
    """`far_line_stacks` output -> the per-line verdict dict. Pure arithmetic on
    already-measured profiles: no image is read, so a threshold sweep is cheap."""
    tol = far_tol_px_720 * s_scale
    out = {}
    for name, (sv, profs, n_samples) in stacks.items():
        zs, offs, hits, dets = [], [], [], []
        for P in profs:
            det, hit, z, off = _seg_hit(sv, P, tol, far_min_z)
            dets.append(det)
            hits.append(hit)
            zs.append(round(z, 3))
            offs.append(None if not np.isfinite(off) else round(off, 4))
        nseg = len(profs)
        n_det = int(np.sum(dets))
        seen = n_det >= max(1, int(np.ceil(min_det_frac * nseg)))
        out[name] = {"frac": float(np.sum(hits) / n_det) if n_det else 0.0,
                     "seen": bool(seen), "n_seg": nseg, "n_det": n_det,
                     "n_samples": n_samples, "z": zs, "off": offs}
    return out


def far_line_profile(grey, cam: CourtCamera, *, far_tol_px_720: float = FAR_TOL_PX_720,
                     far_min_z: float = FAR_MIN_Z, segments: int = 8, min_samples: int = 24,
                     step_px: float = 1.0, reach_px_720: float | None = None,
                     prof_step_px: float = 0.25, min_width_px_720: float = 0.67,
                     clear_m: float = 0.3, min_det_frac: float = 0.5) -> dict:
    """{line name: {"frac", "n_seg", "n_det", "n_samples", "z", "off", "seen"}}
    for the paint that is TOO THIN for the per-point ridge finder - the samples
    `paint_check` drops.

    Reads the image only at offsets FROM the camera's own prediction, so it takes
    no far-line position from the model it checks. `frac` is over the segments in
    which the line was SEEN at all; `seen` is False when fewer than
    `min_det_frac` of the segments found any ridge in the search window, and a
    line that was not seen is not evidence either way. Returns nothing for a line
    whose thin part is out of frame or too short to make one segment.

    `reach_px_720=None` means the REGISTERED window, `FAR_REACH_MULT * far_tol`:
    the search half-width follows the tolerance instead of being set apart from
    it. Pass a number only to reproduce an older run."""
    if reach_px_720 is None:
        reach_px_720 = FAR_REACH_MULT * far_tol_px_720
    st = far_line_stacks(grey, cam, segments=segments, min_samples=min_samples,
                         step_px=step_px, reach_px_720=reach_px_720,
                         prof_step_px=prof_step_px, min_width_px_720=min_width_px_720,
                         clear_m=clear_m)
    return score_far_stacks(st, far_tol_px_720=far_tol_px_720, far_min_z=far_min_z,
                            s_scale=cam.image_wh[1] / 720.0, min_det_frac=min_det_frac)


# ------------------------------------ the STEP-AWARE far-line instrument ---
# Why this exists: at the far baseline the paint is ~0.14 px wide and sits ON the
# court/run-off colour step, so its cross-section is a ~0.7 DN bump riding on a
# ~15 DN step. Every ridge finder above (stacked profile, pyramid) looks for a
# symmetric peak and reads that shape ~1 px off (qa 2026-09-22 s3; job 1's
# run-off scene reproduces it, +0.9-1.2 px). The paint fit already models exactly
# this shape: `paintfit._design` in "kappa" mode is a blurred paint box plus a
# blurred step at the paint's OUTER edge, tied by one ratio kappa = paint /
# (surface - run-off) measured on the strong NEAR baseline. On a boundary line the
# step is then not a confuser but signal: it sits at the line's outer edge, so it
# moves with the line. This reuses that model unchanged, on long stations (one per
# along-line segment), and asks where it puts each segment's paint relative to
# the camera's own prediction. With no step (kappa unmeasurable), `_mode_for`
# falls back to the free-amplitude box, as the paint fit does.
#
# Classification per segment, fixed with the pre-registration (job 2, 2026-09-23):
#   unseen - the model is not significant against a flat profile (paintfit's own
#            `min_dsse`), its paint amplitude is not positive, or its offset is
#            uncertain (`sig_c >= max_sig_c`) while INSIDE the window;
#   miss   - significant, and the offset is past tolerance - INCLUDING a fit that
#            ran to the edge of its search window. G8's bar-3 failure was a far
#            ridge falling out of view and leaving the denominator; here a fit that
#            wants to leave the window is a measured miss, never a non-observation;
#   hit    - significant, |offset| <= tol, `sig_c < max_sig_c`.
# A line is SEEN when at least half its segments are not unseen, and its fraction
# is hits / (hits + misses), decided by paint_check's own `min_line_frac`.
STEPFIT_WINDOW_PX_720 = 3.0     # search half-window, fixed (not swept, not tol-coupled)
STEPFIT_SEGMENTS = 24           # stations that straddle a crossing line are dropped
STEPFIT_MIN_STATION_PX_720 = 16.0
# chosen by G8's rule on G10's dev sweep (seeds 600-605, both scenes): the highest
# catch at <= 1% false flags; ~0.53 px@1080, ~19 cm on the ground at the far baseline
STEPFIT_TOL_PX_720 = 0.35
# The photometry (blur sigma, kappa) is read on the near baseline and near service
# line exactly as `paintfit.estimate_photometry` does, but through a WIDER window:
# the paint fit's 1.5 px assumes a nearly-converged camera, while a check must read
# the photometry of a camera that may be a few px off. Sigma and kappa describe the
# image, not the camera, so the window only has to contain the line.
STEPFIT_PHOTO_WINDOW_PX_720 = 6.0


def _photometry(img, pf, lines, feats, cfg, window_px):
    """`paintfit.estimate_photometry` with the search window as a parameter."""
    parts = []
    for name in ("near_baseline", "near_service"):
        li = [L.name for L in lines].index(name)
        L = lines[li]
        S = paintfit.make_stations(pf, L, ("line", li), (0, 1), 4.0, window_px, cfg.sig_init,
                                   feats, cfg)
        if S is None:
            continue
        P, _ = paintfit._profiles(img, S, L, cfg.sig_init, False, cfg)
        if P is None:
            continue
        mode = "step" if L.outer else "free"
        c0, *_ = paintfit.scan_profiles(P, cfg.sig_init, mode, None, cfg.fine_step)
        parts.append((L, P, mode, c0))
    if not parts:
        return cfg.sig_init, None
    tot = []
    for sg in cfg.sig_grid:
        e = 0.0
        for L, P, mode, c0 in parts:
            e += float(np.nansum(paintfit.refine_profiles(P, sg, mode, None, c0, iters=3)[3]))
        tot.append(e)
    sig = float(cfg.sig_grid[int(np.argmin(tot))])
    kappa = None
    for L, P, mode, c0 in parts:
        if mode != "step":
            continue
        c, sc, beta, sse, s2 = paintfit.refine_profiles(P, sig, mode, None, c0)
        rho = beta[:, 2]
        good = np.isfinite(sc) & (sc < cfg.max_sig_c) & (np.abs(rho) > cfg.kappa_min_step_dn)
        if good.sum() >= 10 and abs(np.median(rho[good])) > cfg.kappa_min_step_dn:
            kappa = float(np.median(beta[good, 1] / rho[good]))
    return sig, kappa


def far_line_stepfit_measure(grey, cam: CourtCamera, *, window_px_720: float = STEPFIT_WINDOW_PX_720,
                             segments: int = STEPFIT_SEGMENTS,
                             min_station_px_720: float = STEPFIT_MIN_STATION_PX_720,
                             photometry: tuple | None = None, cfg=None) -> dict:
    """{"sig", "kappa", "lines": {name: {"c", "sig_c", "sigf", "amp", "win", "mode",
    "n_try"}}} - the paint fit's line model fitted at the camera's OWN prediction
    of each far line, one long station per segment. Measured once; scored per
    tolerance by `score_stepfit`, so a sweep does not re-read the image.

    Reads the image only at offsets FROM the prediction and takes no far-line
    position from the model it checks. `photometry` = (sigma_px, kappa) skips the
    estimate from the near lines (e.g. the setup fit's); None measures it here, on
    this image, at this camera's near lines."""
    cfg = cfg or paintfit.FitConfig
    img = np.asarray(grey, float)
    pf = cam.to_paintfit()
    lines = paintfit.paint_lines()
    marks = paintfit.centre_marks()
    feats = paintfit._features(pf, lines, marks)
    w, h = cam.image_wh
    s_scale = h / 720.0
    if photometry is None:
        sig, kappa = _photometry(img, pf, lines, feats, cfg,
                                 STEPFIT_PHOTO_WINDOW_PX_720 * s_scale)
    else:
        sig, kappa = photometry
    W = window_px_720 * s_scale
    tape_curve, tape_hw = paintfit.measure_tape(img, pf, feats, W, sig, cfg)
    out = {"sig": float(sig), "kappa": None if kappa is None else float(kappa), "lines": {}}
    for li, L in enumerate(lines):
        if L.name not in FAR_LINES:
            continue
        q = paintfit._visible_poly(pf, paintfit._ground_pts3(L, np.linspace(0, 1, 400)))
        if q is None:
            continue
        inf = (q[:, 0] >= 2) & (q[:, 0] < w - 3) & (q[:, 1] >= 2) & (q[:, 1] < h - 3)
        if inf.sum() < 2:
            continue
        qi = q[inf]
        arc = float(np.sum(np.linalg.norm(np.diff(qi, axis=0), axis=1)))
        spacing = max(arc / segments, min_station_px_720 * s_scale)
        S = paintfit.make_stations(pf, L, ("line", li), (0.0, 1.0), spacing, W, sig, feats, cfg)
        if S is None:
            continue
        P, idx = paintfit._profiles(img, S, L, sig, False, cfg, tape_curve, tape_hw)
        if P is None:
            continue
        mode = paintfit._mode_for(L, False, kappa)
        c0, _, sse0, _ = paintfit.scan_profiles(P, sig, mode, kappa, cfg.fine_step)
        c, sig_c, beta, sse, s2 = paintfit.refine_profiles(P, sig, mode, kappa, c0)
        with np.errstate(invalid="ignore", divide="ignore"):
            sigf = (sse0 - sse) / s2
        out["lines"][L.name] = {
            "c": c.tolist(), "sig_c": sig_c.tolist(), "sigf": sigf.tolist(),
            "amp": paintfit._paint_amp(beta, mode, kappa).tolist(),
            "win": S.win[idx].tolist(), "mode": mode, "n_try": int(len(idx))}
    return out


def score_stepfit(meas: dict, *, far_tol_px_720: float = STEPFIT_TOL_PX_720, s_scale: float = 1.0,
                  min_det_frac: float = 0.5, cfg=None) -> dict:
    """`far_line_stepfit_measure` output -> the per-line verdict dict, in the same
    shape as `score_far_stacks` ("frac", "seen", "n_seg", "n_det", "n_samples")
    plus the per-segment class. Pure arithmetic on the measurement."""
    cfg = cfg or paintfit.FitConfig
    tol = far_tol_px_720 * s_scale
    out = {}
    for name, m in meas["lines"].items():
        c, sc, sf = np.asarray(m["c"]), np.asarray(m["sig_c"]), np.asarray(m["sigf"])
        amp, win = np.asarray(m["amp"]), np.asarray(m["win"])
        sig = np.isfinite(sf) & (sf > cfg.min_dsse) & (amp > 0) & np.isfinite(c)
        edge = np.abs(c) >= win - 0.02
        cls = np.where(~sig, "unseen",
                       np.where(edge, "miss",
                                np.where(~(np.isfinite(sc) & (sc < cfg.max_sig_c)), "unseen",
                                         np.where(np.abs(c) <= tol, "hit", "miss"))))
        n_hit, n_miss = int((cls == "hit").sum()), int((cls == "miss").sum())
        n_det = n_hit + n_miss
        nseg = len(c)
        seen = nseg > 0 and n_det >= max(1, int(np.ceil(min_det_frac * nseg)))
        out[name] = {"frac": float(n_hit / n_det) if n_det else 0.0, "seen": bool(seen),
                     "n_seg": nseg, "n_det": n_det, "n_samples": m["n_try"],
                     "class": cls.tolist(), "off": [round(float(x), 4) for x in c],
                     "mode": m["mode"]}
    return out


def far_line_stepfit(grey, cam: CourtCamera, *, far_tol_px_720: float = STEPFIT_TOL_PX_720,
                     min_det_frac: float = 0.5, **kw) -> dict:
    """Measure and score in one call; the drop-in for `far_line_profile`."""
    meas = far_line_stepfit_measure(grey, cam, **kw)
    return score_stepfit(meas, far_tol_px_720=far_tol_px_720,
                         s_scale=cam.image_wh[1] / 720.0, min_det_frac=min_det_frac)


FAR_MODES = ("stack", "stepfit")
FAR_MODE_DEFAULT = "stepfit"     # G10 PASS, 2026-09-23 (was "stack")


@dataclass
class PaintCheck:
    ok: bool
    support: float                 # over every WIDE sample on a checked line
    lines: dict                    # name -> (fraction on paint, n samples)
    unchecked: list                # lines too thin (or out of frame) to check
    worst: str | None
    scope: str = "none"            # whole_court | near_half | none
    checked: list = field(default_factory=list)
    far: dict = field(default_factory=dict)     # far_line_profile detail
    detail: dict = field(default_factory=dict)  # name -> {"wide": ..., "thin": ...}

    @property
    def far_lines_checked(self) -> bool:
        return all(n in self.lines for n in FAR_LINES)

    def claim(self) -> str:
        """One sentence saying WHAT was verified - never just yes/no."""
        if not self.ok:
            return f"not verified ({self.worst or 'nothing checkable'})"
        if self.scope == "whole_court":
            return "whole court verified against the paint"
        miss = ", ".join(self.unchecked) or "some lines"
        return f"near half verified; NOT verified: {miss}"


def paint_check(grey, cam: CourtCamera, *, tol_px_720: float = 1.5, min_dn: float = 6.0,
                min_line_frac: float = 0.5, min_width_px_720: float = 0.67,
                min_samples: int = 6, min_across: int = 2, min_along: int = 2,
                step_m: float = 0.4, far_lines: bool = FAR_LINES_DEFAULT,
                far_kw: dict | None = None, far_mode: str = FAR_MODE_DEFAULT,
                far_scored: dict | None = None) -> PaintCheck:
    """Does `cam` put the court ON THE PAINT? For every painted line whose
    projected paint is at least `min_width_px_720` wide, the fraction of its
    in-frame samples with a paint ridge within `tol_px_720` of where `cam` puts
    them. Paint THINNER than that - the far baseline and far service line, whose
    5 cm runs in depth and projects under a pixel - is measured by
    `far_line_profile`, which integrates ALONG the line instead (G8); with
    `far_lines=False` those lines go back to being listed `unchecked`, which is
    the pre-G8 behaviour. A line measured both ways takes the WORSE fraction.
    `ok` needs EVERY checked line >= `min_line_frac`:
    a court slid in depth keeps its long sidelines on paint and loses one
    baseline, which a court-wide average hides. It also needs at least
    `min_across` checkable cross-court lines and `min_along` long lines: a camera
    that pushes lines OUT of the frame must not pass by leaving nothing to check.

    An INDEPENDENT lock check - it reads the image at the camera's own
    predictions over the whole court, not at points a tracker chose - and a
    lock/no-lock signal only, never an accuracy measure (rule 1). Thresholds
    were set on DEVELOPMENT seeds of the synthetic scene and are scored on that
    same scene (docs/evidence/court-camera3d.md, G5; qa flagged the circularity
    in the 2026-09-18 audit). The structure guard below is load-bearing."""
    world, wdir, ids, names, widths = _samples(step_m)
    w, h = cam.image_wh
    s = h / 720.0
    uv = cam.project(world)
    inb = np.isfinite(uv).all(1) & (uv[:, 0] >= 8) & (uv[:, 0] < w - 8) &         (uv[:, 1] >= 8) & (uv[:, 1] < h - 8)
    nrm = np.zeros_like(uv)
    wpx = np.zeros(len(world))
    if inb.any():
        nrm[inb] = line_normals(cam, world[inb], wdir[inb])
        n3 = np.column_stack([-wdir[inb, 1], wdir[inb, 0], np.zeros(inb.sum())])
        half = (widths[ids[inb]] / 2.0)[:, None]
        wpx[inb] = np.linalg.norm(cam.project(world[inb] + n3 * half)
                                  - cam.project(world[inb] - n3 * half), axis=1)
    use = inb & (wpx >= min_width_px_720 * s)
    lines, unchecked, detail = {}, [], {}
    hits = np.zeros(len(world), bool)
    if use.any():
        tol = tol_px_720 * s
        off, found = ridge_offsets(grey, uv[use], nrm[use], 3.0 * tol, min_dn)
        hits[use] = found & (np.abs(off) <= tol)
    if far_mode not in FAR_MODES:
        raise ValueError(f"far_mode {far_mode!r} not in {FAR_MODES}")
    if not far_lines:
        far = {}
    elif far_scored is not None:
        # an already-SCORED far-line dict (a sweep re-scoring one measurement per
        # threshold); it must come from this image and this camera
        far = far_scored
    elif far_mode == "stepfit":
        # the whole far line, not just its sub-pixel part: the model knows its width
        far = far_line_stepfit(grey, cam, **(far_kw or {}))
    else:
        far = far_line_profile(grey, cam, min_width_px_720=min_width_px_720, **(far_kw or {}))
    for i, nm in enumerate(names):
        m = use & (ids == i)
        wide = (float(hits[m].mean()), int(m.sum())) if m.sum() >= min_samples else None
        thin = far.get(nm)
        if thin is not None and not thin["seen"]:
            thin = None          # too faint to SEE is not evidence of a wrong camera
        if wide is None and thin is None:
            unchecked.append(nm)
            continue
        d = {}
        if wide is not None:
            d["wide"] = wide
        if thin is not None:
            d["thin"] = (thin["frac"], thin["n_samples"], thin["n_seg"])
        detail[nm] = d
        frac = min([v[0] for v in d.values()])
        lines[nm] = (float(frac), int(sum(v[1] for v in d.values())))
    if not lines:
        return PaintCheck(False, float("nan"), {}, unchecked, None, "none", [], far, detail)
    worst = min(lines, key=lambda k: lines[k][0])
    checked = use & np.isin(ids, [names.index(k) for k in lines])
    across = sum(1 for k in lines if abs(wdir[ids == names.index(k)][0, 0]) > 0.5)
    ok = (lines[worst][0] >= min_line_frac and across >= min_across
          and len(lines) - across >= min_along)
    if lines[worst][0] >= min_line_frac and not ok:
        worst = "too_few_lines"
    # `support` is over WIDE samples only - but "checked" means every line in
    # `lines`, and with the far lines ON a far line that becomes checked brings its
    # few WIDE samples in with it. So with far_lines=False it is exactly the number
    # G7 scored; with them ON it can move (qa 2026-09-19: 4 of 400 CP1 trials, by
    # up to 0.0114, at the 8.0 px window; 0 of 400 at the registered window).
    sup = float(hits[checked].mean()) if checked.any() else float("nan")
    scope = "whole_court" if not unchecked else "near_half"
    return PaintCheck(ok, sup, lines, unchecked, worst, scope, sorted(lines), far, detail)


def paint_support(grey, cam: CourtCamera, **kw) -> float:
    """Court-wide fraction of checkable paint samples that sit on paint."""
    return paint_check(grey, cam, **kw).support


def dolly_zoom(cam: CourtCamera, scale: float) -> CourtCamera:
    """`cam` with focal length x `scale` and its centre moved along the optical
    axis so that the court's centre keeps its image position and size: the
    direction in which a court fitted to its sidelines is least constrained in
    depth."""
    c = np.array([court.X_CENTER, court.NET_Y, 0.0])
    R = cam.R
    z_c = float((R @ c + cam.tvec)[2])
    Cn = cam.position_m() - (scale - 1.0) * z_c * R[2]
    return CourtCamera(cam.f_px * scale, cam.rvec, -R @ Cn, cam.image_wh, cam.lens,
                       cam.dist, cam.pinned_by, dict(cam.extra))


def shifted(cam: CourtCamera, dx_m: float) -> CourtCamera:
    """`cam` moved `dx_m` across the court, orientation kept: a court fitted
    one alley over (singles and doubles sidelines swapped)."""
    C = cam.position_m() + [dx_m, 0.0, 0.0]
    return CourtCamera(cam.f_px, cam.rvec, -cam.R @ C, cam.image_wh, cam.lens, cam.dist,
                       cam.pinned_by, dict(cam.extra))


RESTARTS = (("dolly", 1.15), ("dolly", 0.87), ("dolly", 1.33), ("dolly", 0.75),
            ("shift", court.ALLEY), ("shift", -court.ALLEY))


def fit_camera_checked(frames, seed: CourtCamera, *, restarts=RESTARTS, cfg=None,
                       pose_only: bool = False) -> PaintFitResult:
    """`fit_camera_on_paint`, then `paint_check`; when the check fails, re-fit
    from variants of the seed along the two known false-basin directions (a
    dolly-zoom in depth, a one-alley shift across) and keep the first that
    passes, else the one whose worst line is best. `pose_only` never restarts.
    `result.camera.extra` records `paint_check` ("pass" / "FAIL:<line>") and
    `starts`. A FAIL is a court the app must treat as NOT LOCKED."""
    grey = np.clip(grey_mean(frames), 0, 255).astype(np.uint8)
    tried = []
    for k, rs in enumerate((None,) + tuple(restarts)):
        if k and pose_only:
            break
        start = (seed if rs is None else
                 dolly_zoom(seed, rs[1]) if rs[0] == "dolly" else shifted(seed, rs[1]))
        try:
            res = fit_camera_on_paint(grey.astype(float), start, pose_only=pose_only, cfg=cfg)
        except Exception:
            continue
        chk = paint_check(grey, res.camera)
        tried.append((chk, res))
        if chk.ok:
            break
    if not tried:
        raise RuntimeError("paint fit failed from every start")
    chk, res = max(tried, key=lambda cr: (cr[0].ok, min((v[0] for v in cr[0].lines.values()),
                                                         default=-1.0)))
    res.camera.extra.update(paint_check="pass" if chk.ok else f"FAIL:{chk.worst}",
                            starts=len(tried),
                            # WHAT was verified, carried into setup.camera and
                            # so into match.json (G8, hard rule 5)
                            lock_scope=chk.scope,
                            lock_unverified=list(chk.unchecked),
                            lock_claim=chk.claim())
    return res


# --------------------------------------------- height-prior seeding (G12) --
# The founder's Phase 2 (job 4, 2026-09-23; DECISIONS_PENDING item 3): G1's wrong
# cameras are DISCRETE basins along a dolly-zoom (f -13.7% at height 3.39 m recurs
# 5 times), predicted by the seed's height error. So launch the fit from several
# fixed camera heights and let the INDEPENDENT on-paint check pick the winner -
# never the fit's own cost, which G7 measured inverted (it prefers the wrong
# camera). Setup only: 3 fits cost 3x, once.
HEIGHT_PRIORS_M = (1.5, 2.5, 3.5)


def at_height(cam: CourtCamera, height_m: float, scale_range=(0.3, 3.0)) -> CourtCamera | None:
    """`cam` dolly-zoomed (`dolly_zoom`: the court centre keeps its image position
    and size) until its centre is `height_m` above the court. None when that needs
    a zoom outside `scale_range` or the camera does not look down."""
    c = np.array([court.X_CENTER, court.NET_Y, 0.0])
    R = cam.R
    z_c = float((R @ c + cam.tvec)[2])
    down = float(R[2][2])                 # optical axis, world z component
    if z_c <= 0 or down >= -1e-6:
        return None
    s = 1.0 + (float(cam.position_m()[2]) - height_m) / (z_c * down)
    if not scale_range[0] <= s <= scale_range[1]:
        return None
    return dolly_zoom(cam, s)


def fit_camera_anchored(frames, seed: CourtCamera, *, heights=HEIGHT_PRIORS_M,
                        cfg=None) -> PaintFitResult:
    """One `fit_camera_on_paint` from `seed` moved to each prior height, and the
    winner chosen by `paint_check` alone: a passing camera beats a failing one,
    then the best worst-line fraction, then support. The fits' own costs are not
    consulted. `camera.extra` records every anchor's outcome and which won; a FAIL
    is a court the app must treat as NOT LOCKED."""
    grey = np.clip(grey_mean(frames), 0, 255).astype(np.uint8)
    tried, log = [], []
    for h in heights:
        start = at_height(seed, h)
        if start is None:
            log.append({"height_m": h, "fit": "anchor unreachable"})
            continue
        try:
            res = fit_camera_on_paint(grey.astype(float), start, cfg=cfg)
        except Exception as ex:
            log.append({"height_m": h, "fit": f"failed: {ex!r}"})
            continue
        chk = paint_check(grey, res.camera)
        wf = min((v[0] for v in chk.lines.values()), default=-1.0)
        tried.append((chk, wf, res, h))
        log.append({"height_m": h, "ok": bool(chk.ok), "worst_frac": float(wf),
                    "support": float(chk.support), "f_px": float(res.camera.f_px),
                    "fitted_height_m": float(res.camera.position_m()[2])})
    if not tried:
        raise RuntimeError("paint fit failed from every height prior")
    chk, wf, res, h = max(tried, key=lambda t: (t[0].ok, t[1], np.nan_to_num(t[0].support, nan=-1.0)))
    res.camera.extra.update(paint_check="pass" if chk.ok else f"FAIL:{chk.worst}",
                            starts=len(tried), height_prior_m=h, anchors=log,
                            lock_scope=chk.scope, lock_unverified=list(chk.unchecked),
                            lock_claim=chk.claim())
    return res
