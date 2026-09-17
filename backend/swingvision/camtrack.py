"""Live court tracking as a moving CAMERA: the court never moves, the phone does.

Founder ruling 2026-09-17 (docs/SPEC.md s1): when the phone moves, the court is
"still there but just shaped differently" - keep tracking and re-fitting; never
stop, never ask for a re-tap. So the tracked quantity is the camera's pose
(R_t, t_t). Focal length and lens are held from setup (a fixed-zoom phone).

Per frame:
  1. FLOW  - points along the painted lines, where the last camera put them,
             followed into this frame by pyramidal Lucas-Kanade (forward-backward
             checked; player boxes masked), then a RANSAC PnP gives a measured pose.
  2. SMOOTH - a constant-velocity Kalman filter on the 6-DOF pose absorbs fence
             sway and wind without jumping the court grid.
  3. RE-FIT - paintfit's whole-court fit, pose only, from the filtered pose, when
             the SPEC s1 drift test fires (tracked-point error over `drift_px`
             for `drift_frames` frames) or every `refit_s` seconds.
  4. RECOVER - when flow loses the court: detector -> PnP seed -> paint fit.
             Until that succeeds the last good camera is held. It never calls
             `courtfit.autodetect`, the search recorded CLOSED (SPEC s1, rule 3).

EVERY THRESHOLD HERE IS UNMEASURED. SPEC s1's numbers were set for another
mechanism; researcher found 15 px is ~5 m at the far baseline at 1080p/3 m.
tools/court_track_sim.py is the pre-registered measurement.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import camera3d, court, paintfit


PINNED_TRACK = ("tracked: paint points followed by optical flow from the last paint fit + "
                "PnP with that fit's focal length and lens held + Kalman smoothing")


@dataclass
class TrackConfig:
    drift_px_720: float = 10.0      # SPEC s1's 15 px, read at 1080p; scales by height/720
    drift_frames: int = 3           # SPEC s1: sustained, not a one-frame spike
    refit_s: float = 10.0           # SPEC s1 backstop
    sample_step_m: float = 0.4      # spacing of tracked points along the lines
    min_tracked: int = 12
    lost_frac: float = 0.35         # fewer surviving points than this -> recover
    fb_max_px: float = 1.0          # forward-backward LK consistency
    ridge_px_720: float = 6.0       # paint search either side of the flowed point
    ridge_min_dn: float = 6.0       # paint must stand this far above its surround
    ransac_px_720: float = 3.0
    q_rot: float = 1e-2             # process noise (white acceleration), rad^2 s^-3
    q_pos: float = 1e-2             # m^2 s^-3
    r_floor_px: float = 0.1         # measurement noise floor, px rms


@dataclass
class TrackStep:
    camera: camera3d.CourtCamera
    status: str          # tracking | refit | recovered | holding
    n_tracked: int
    resid_px: float


class _PoseKalman:
    """Constant-velocity filter on x = [rvec, tvec, d rvec/dt, d tvec/dt]."""

    def __init__(self, rvec, tvec, cfg: TrackConfig):
        self.cfg = cfg
        self.reset(rvec, tvec)

    def reset(self, rvec, tvec):
        self.x = np.concatenate([rvec, tvec, np.zeros(6)])
        self.P = np.diag([1e-6] * 3 + [1e-4] * 3 + [1e-4] * 3 + [1e-2] * 3)

    def step(self, dt, z, r_rot, r_pos):
        c = self.cfg
        F = np.eye(12)
        F[:6, 6:] = np.eye(6) * dt
        q = np.array([c.q_rot] * 3 + [c.q_pos] * 3)
        Q = np.zeros((12, 12))            # white-acceleration model per axis
        Q[:6, :6] = np.diag(q * dt ** 3 / 3)
        Q[:6, 6:] = Q[6:, :6] = np.diag(q * dt ** 2 / 2)
        Q[6:, 6:] = np.diag(q * dt)
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q
        if z is None:
            return self.x[:3], self.x[3:6]
        z = np.asarray(z, float)
        R = np.diag([r_rot] * 3 + [r_pos] * 3)
        Hm = np.zeros((6, 12))
        Hm[:, :6] = np.eye(6)
        S = Hm @ self.P @ Hm.T + R
        K = self.P @ Hm.T @ np.linalg.inv(S)
        self.x = self.x + K @ (z - Hm @ self.x)
        self.P = (np.eye(12) - K @ Hm) @ self.P
        return self.x[:3], self.x[3:6]


def _grey8(frame):
    import cv2
    g = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return g if g.dtype == np.uint8 else np.clip(g, 0, 255).astype(np.uint8)


class CameraTracker:
    """Track a CourtCamera through a video. `detector` (a
    courtfit.KeypointDetector) is used only to recover from a big change; with
    None the tracker holds the last good camera and keeps trying to re-fit.
    `paint_fit(frames, seed, pose_only)` is injectable for tests."""

    def __init__(self, cam0: camera3d.CourtCamera, detector=None,
                 cfg: TrackConfig | None = None, paint_fit=None):
        from . import courtfit
        if isinstance(detector, courtfit.ClassicalKeypoints):
            raise ValueError("ClassicalKeypoints runs courtfit.autodetect, the search "
                             "recorded CLOSED; SPEC s1 bars it from recovery")
        self.cfg = cfg or TrackConfig()
        self.detector = detector
        self.paint_fit = paint_fit or camera3d.fit_camera_on_paint
        self.cam = cam0
        self.good = cam0
        self.kf = _PoseKalman(cam0.rvec, cam0.tvec, self.cfg)
        self.prev = None
        self.t_prev = None
        self.t_refit = None
        self.drift_run = 0
        self.scale = cam0.image_wh[1] / 720.0
        self.world, self.wdir = _paint_samples(self.cfg.sample_step_m)

    def _like(self, rvec, tvec, pinned):
        c = self.cam
        return camera3d.CourtCamera(c.f_px, rvec, tvec, c.image_wh, c.lens, c.dist, pinned,
                                    dict(c.extra))

    def _visible(self, cam):
        uv = cam.project(self.world)
        w, h = cam.image_wh
        ok = np.isfinite(uv).all(1) & (uv[:, 0] >= 2) & (uv[:, 0] < w - 2) &             (uv[:, 1] >= 2) & (uv[:, 1] < h - 2)
        return ok, uv

    def _normals(self, cam, idx):
        """Unit image normals (undistorted frame) of each sample's line."""
        pf = cam.to_paintfit()
        a, _ = pf.to_undist(self.world[idx])
        b, _ = pf.to_undist(self.world[idx] + 0.05 * self.wdir[idx])
        d = b - a
        d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
        return np.column_stack([-d[:, 1], d[:, 0]])

    def _flow(self, grey, boxes):
        import cv2
        ok, uv = self._visible(self.cam)
        for b in boxes or []:
            if b is None:
                continue
            x1, y1, x2, y2 = b
            ok &= ~((uv[:, 0] >= x1) & (uv[:, 0] <= x2) & (uv[:, 1] >= y1) & (uv[:, 1] <= y2))
        idx = np.flatnonzero(ok)
        if len(idx) < self.cfg.min_tracked:
            return None, len(idx)
        p0 = uv[idx].astype(np.float32).reshape(-1, 1, 2)
        lk = dict(winSize=(21, 21), maxLevel=3,
                  criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
        p1, st, _ = cv2.calcOpticalFlowPyrLK(self.prev, grey, p0, None, **lk)
        pb, stb, _ = cv2.calcOpticalFlowPyrLK(grey, self.prev, p1, None, **lk)
        # the along-line component is unobservable on a straight line (aperture),
        # so both the consistency test and the pose use only the NORMAL component
        nrm = self._normals(self.cam, idx)
        fb = np.abs(np.sum((pb - p0).reshape(-1, 2) * nrm, axis=1))
        keep = (st.ravel() == 1) & (stb.ravel() == 1) & (fb <= self.cfg.fb_max_px * self.scale)
        # flow only PREDICTS; each point is then snapped onto the paint itself,
        # along its line's normal, so the measurement is anchored to the court
        # and errors cannot accumulate from frame to frame
        p1 = p1.reshape(-1, 2).astype(float)
        off, found = _ridge(grey, p1, nrm, self.cfg.ridge_px_720 * self.scale,
                            self.cfg.ridge_min_dn)
        keep &= found
        if keep.sum() < max(self.cfg.min_tracked, self.cfg.lost_frac * len(idx)):
            return None, int(keep.sum())
        p1 = p1 + off[:, None] * nrm
        return (idx[keep], p1[keep]), int(keep.sum())

    def _normal_resid(self, cam, idx, und):
        pf = cam.to_paintfit()
        uv, z = pf.to_undist(self.world[idx])
        r = np.sum((uv - und) * self._normals(cam, idx), axis=1)
        return np.where(z > 0, r, 1e3)

    def _pose_from(self, idx, img):
        """Pose minimising the robust NORMAL distance of each flowed point to where
        its line projects. Focal length and lens held."""
        from scipy import optimize
        und = self.cam.undistort(img)
        thr = self.cfg.ransac_px_720 * self.scale

        def res(p):
            return self._normal_resid(self._like(p[:3], p[3:], ""), idx, und)
        x0 = np.concatenate([self.cam.rvec, self.cam.tvec])
        sol = optimize.least_squares(res, x0, loss="cauchy", f_scale=thr, x_scale="jac",
                                     max_nfev=60)
        r = res(sol.x)
        inl = np.abs(r) <= thr
        if inl.sum() < self.cfg.min_tracked:
            return None
        return sol.x[:3], sol.x[3:], float(np.sqrt(np.mean(r[inl] ** 2)))

    def _refit(self, frame, seed):
        try:
            return self.paint_fit(frame, seed, pose_only=True).camera
        except Exception:
            return None

    def _recover(self, frame):
        if self.detector is None:
            return None
        try:
            kps = self.detector.detect(frame)
            if kps is None:
                return None
            s = camera3d.solve_pnp_seed(kps, self.cam.image_wh, f_hint=self.cam.f_px)
        except Exception:
            return None
        if s is None:
            return None
        return self._refit(frame, self._like(s.camera.rvec, s.camera.tvec,
                                             camera3d.PINNED_PNP))

    def _adopt(self, cam, t):
        self.cam = self.good = cam
        self.kf.reset(cam.rvec, cam.tvec)
        self.t_refit = t
        self.drift_run = 0

    def step(self, frame, t: float, boxes=None) -> TrackStep:
        grey = _grey8(frame)
        if self.prev is None:
            self.prev, self.t_prev, self.t_refit = grey, t, t
            return TrackStep(self.cam, "tracking", 0, 0.0)
        dt = max(t - self.t_prev, 1e-3)
        got, n = self._flow(grey, boxes)
        pose = self._pose_from(*got) if got is not None else None
        status, resid = "tracking", math.nan
        if pose is None:
            cam = self._recover(frame)
            if cam is not None:
                self._adopt(cam, t)
                status = "recovered"
            else:
                self.cam = self.good
                self.kf.reset(self.good.rvec, self.good.tvec)
                status = "holding"
        else:
            rvec, tvec, r = pose
            # 1 px of image error ~ 1/f rad of rotation, ~ D/f m of position
            r = max(r, self.cfg.r_floor_px) / self.cam.f_px
            dist = float(np.linalg.norm(self.cam.position_m()
                                        - [court.X_CENTER, court.NET_Y, 0.0]))
            rf, tf = self.kf.step(dt, np.concatenate([rvec, tvec]), r ** 2, (r * dist) ** 2)
            self.cam = self._like(rf, tf, PINNED_TRACK)
            idx, img = got
            resid = float(np.median(np.abs(self._normal_resid(
                self.cam, idx, self.cam.undistort(img)))))
            self.drift_run = self.drift_run + 1 if resid > self.cfg.drift_px_720 * self.scale else 0
            due = t - self.t_refit >= self.cfg.refit_s
            if self.drift_run >= self.cfg.drift_frames or due:
                cam = self._refit(frame, self.cam)
                if cam is not None:
                    self._adopt(cam, t)
                    status = "refit"
                else:
                    self.t_refit = t          # do not retry every frame
                    self.good = self.cam
            else:
                self.good = self.cam
        self.prev, self.t_prev = grey, t
        return TrackStep(self.cam, status, n, resid)


def _ridge(grey, pts, nrm, reach, min_dn, step=0.5):
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


def _paint_samples(step_m, clear_m=0.3):
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


def ground_lines_px(cam: camera3d.CourtCamera, n: int = 50) -> list:
    """Every court line (court.LINES) projected through `cam`, as polylines -
    distortion bends them, so a line is drawn as n points, not two."""
    out = []
    for a, b in court.LINES:
        t = np.linspace(0, 1, n)[:, None]
        xy = (1 - t) * np.array(a) + t * np.array(b)
        out.append(cam.project(np.column_stack([xy, np.zeros(n)])))
    return out
