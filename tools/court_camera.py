"""court_camera.py — the court-only camera helpers, lifted VERBATIM from the main repository.

In the main repository these live inside the ball code: `frame_the_court` and the constants in
`tools/height_curve.py`, `to_court_xy` and `CORNERS` in `tools/synth_truth.py`, and
`camera_from_court_corners` in `ball_physics/tennis_tracker/bridge.py` (with `Camera` from
`data/camera.py` and `homography_from_points` from `calibration/court.py`). They are pure court
geometry, so the court repository carries them on their own. Bodies are unchanged; the C1 output
reproduces byte-for-byte (see docs/STATE.md).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

CORNERS = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
SETBACK_M = 6.0
HFOV_DEG = 100.0


def frame_the_court(height_m, setback_m, hfov_deg, w, h):
    """Corner pixels for a centre-line camera at `height_m`, tilted to frame the
    court — or None if this setup cannot see all four corners.

    The pitch is SOLVED, not assumed: bisect until the court's vertical midpoint
    sits at the frame centre. Holding pitch fixed instead would confound the
    thing being measured, since the same tilt frames a 1 m camera and a 12 m one
    completely differently.
    """
    from swingvision import court, courtfit

    f = (w / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)

    def corners_at(pitch):
        p = (court.DOUBLES_WIDTH / 2.0, -setback_m, height_m, 0.0, pitch, f)
        return courtfit._cam_corners(p, w, h, court)

    def offset(pitch):
        """Court's vertical centre minus the frame's. Monotone decreasing in
        pitch (tilting down moves the court up), so bisection is safe."""
        c = corners_at(pitch)
        if c is None:
            return None
        near = (c["near_bl_doubles"][1] + c["near_br_doubles"][1]) / 2.0
        far = (c["far_bl_doubles"][1] + c["far_br_doubles"][1]) / 2.0
        return (near + far) / 2.0 - h / 2.0

    lo, hi = 0.0, math.radians(85.0)
    if (o := offset(lo)) is None or o < 0:
        return None                       # court already above centre at zero tilt
    for _ in range(60):
        mid = (lo + hi) / 2.0
        o = offset(mid)
        if o is None or o < 0:
            hi = mid
        else:
            lo = mid
    c = corners_at(lo)
    if c is None:
        return None
    if not all(0 <= c[n][0] < w and 0 <= c[n][1] < h for n in CORNERS):
        return None                       # a corner off-frame: not a usable setup
    return {n: [float(c[n][0]), float(c[n][1])] for n in CORNERS}, math.degrees(lo)


def to_court_xy(fw_xy):
    """tennis_tracker (physics) frame -> swingvision court frame, in metres.

    THE TWO FRAMES ARE NOT THE SAME, and conflating them is not a subtle error:
      swingvision   x = width  0..10.97, y = length 0..23.77, origin near-left
      tennis_tracker X = length 0..23.77, Y = width +5.485..-5.485 (to image LEFT),
                     origin at the near-baseline centre, +Z up so gravity works
    The simulator lives in the second; analytics.line_call and image_to_court live
    in the first. The first version of this tool compared a physics-frame bounce
    against a court-frame estimate and reported a 30 m median error on a 23.77 m
    court — absurd enough to catch, which is the only reason it was caught.

    Exact inverse of speedspin._to_framework_xy; asserted at startup so the pair
    cannot drift apart (that file already says "change both together").
    """
    return (5.485 - float(fw_xy[1]), float(fw_xy[0]))


@dataclass
class Camera:
    K: np.ndarray            # (3,3) intrinsics
    R: np.ndarray            # (3,3) world->camera rotation
    t: np.ndarray            # (3,)  world->camera translation (camera center C: t = -R C)
    width: int = 1280
    height: int = 720

    @property
    def center(self) -> np.ndarray:
        return -self.R.T @ self.t

    def project(self, pts_w: np.ndarray) -> np.ndarray:
        """World points (N,3) -> pixel coords (N,2). Points behind camera -> NaN."""
        pts_w = np.atleast_2d(pts_w)
        pc = (self.R @ pts_w.T + self.t[:, None]).T      # (N,3) camera coords
        z = pc[:, 2:3]
        uvw = (self.K @ pc.T).T
        uv = uvw[:, :2] / uvw[:, 2:3]
        uv[(z[:, 0] <= 0)] = np.nan
        return uv

    def ray(self, uv: np.ndarray) -> np.ndarray:
        """Pixel -> unit ray direction in world coords (from camera center)."""
        uv = np.atleast_2d(uv).astype(float)
        ones = np.ones((uv.shape[0], 1))
        d_cam = (np.linalg.inv(self.K) @ np.hstack([uv, ones]).T).T   # (N,3)
        d_world = (self.R.T @ d_cam.T).T
        return d_world / np.linalg.norm(d_world, axis=1, keepdims=True)


def homography_from_points(image_pts: np.ndarray, world_pts: np.ndarray):
    """H mapping world-plane (x,y) -> image (u,v) using >=4 correspondences."""
    if cv2 is None:
        raise RuntimeError("OpenCV required for homography")
    image_pts = np.asarray(image_pts, np.float32)
    world_pts = np.asarray(world_pts, np.float32)
    H, _ = cv2.findHomography(world_pts, image_pts, cv2.RANSAC, 5.0)
    return H


_OUR2FW = {
    "near_bl_doubles": [0.0, +5.485],
    "near_br_doubles": [0.0, -5.485],
    "far_bl_doubles": [23.77, +5.485],
    "far_br_doubles": [23.77, -5.485],
}


def camera_from_court_corners(named_corners: dict, img_wh, hfov_deg: float = 70.0):
    """Build (Camera, homography) from the 4 named doubles-corner pixels.

    `named_corners`: {clone landmark name: [u, v]} for the four doubles corners.
    `img_wh`: (width, height). `hfov_deg`: horizontal field of view (see note).
    """
    keys = [k for k in _OUR2FW if k in named_corners]
    if len(keys) < 4:
        raise ValueError("need the 4 doubles corners (near/far _bl/_br_doubles)")
    img = np.array([named_corners[k] for k in keys], np.float32)
    w3d = np.array([[*_OUR2FW[k], 0.0] for k in keys], np.float32)
    w2d = np.array([_OUR2FW[k] for k in keys], np.float32)

    W, H = img_wh
    f = (W / 2.0) / np.tan(np.radians(hfov_deg) / 2.0)
    K = np.array([[f, 0, W / 2.0], [0, f, H / 2.0], [0, 0, 1.0]])

    # All four corners are coplanar, so the pose is TWO-FOLD AMBIGUOUS: a camera
    # above the court and its mirror below it reproject identically. Projection
    # cannot tell them apart — but physics can't survive the wrong one, because
    # gravity is -z and the mirrored frame has +z pointing into the ground. This
    # was shipping silently: plain solvePnP was returning the below-ground pose
    # for yt_rally2 (camera centre z = -3.3 m), so every arc was fitted with
    # gravity effectively inverted. Ask IPPE for both solutions and keep the one
    # with the camera above the court, breaking ties on reprojection error.
    ok, rvecs, tvecs, errs = cv2.solvePnPGeneric(w3d, img, K, None,
                                                 flags=cv2.SOLVEPNP_IPPE)
    if not ok or not len(rvecs):
        ok, rvec, tvec = cv2.solvePnP(w3d, img, K, None, flags=cv2.SOLVEPNP_ITERATIVE)
        if not ok:
            raise RuntimeError("solvePnP failed for the court corners")
        rvecs, tvecs, errs = [rvec], [tvec], [np.array([0.0])]

    best = None
    for i, (rv, tv) in enumerate(zip(rvecs, tvecs)):
        R, _ = cv2.Rodrigues(rv)
        t = tv[:, 0]
        centre_z = float((-R.T @ t)[2])
        err = float(np.ravel(errs[i])[0]) if i < len(errs) else 0.0
        key = (centre_z <= 0.0, err)        # above-ground first, then lowest error
        if best is None or key < best[0]:
            best = (key, R, t, centre_z)
    _, R, t, centre_z = best
    # IPPE is analytic; polish the winner so corner reprojection matches what the
    # iterative solver used to give (sub-pixel), without reopening the ambiguity.
    rv, _ = cv2.Rodrigues(R)
    rv, tv = cv2.solvePnPRefineLM(w3d, img, K, None, rv, t.reshape(3, 1).copy())
    R_ref, _ = cv2.Rodrigues(rv)
    if float((-R_ref.T @ tv[:, 0])[2]) > 0.0:
        R, t = R_ref, tv[:, 0]
        centre_z = float((-R.T @ t)[2])
    if centre_z <= 0.0:
        raise RuntimeError(
            f"no above-court camera pose for these corners (centre z={centre_z:.2f} m); "
            "physics cannot be fitted in a frame where gravity points up")
    cam = Camera(K=K, R=R, t=t, width=int(W), height=int(H))
    Hh = homography_from_points(img, w2d)
    return cam, Hh
