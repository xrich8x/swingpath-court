"""Physical shape lock (swingvision.courtfit.cam_fit_quad).

The manual overlay lets a human drag 4 corners freely (8 DOF); cam_fit_quad must
project any such quad onto the closest 6-DOF physical camera view of a
regulation court. Two guarantees are tested:
  1. an already-physical quad passes through (near-)unchanged, and
  2. an impossible quad (one corner yanked) comes back as a legal camera shape —
     re-fitting the OUTPUT finds a ~0px camera residual.
"""

import math

import numpy as np
import pytest

pytest.importorskip("cv2")
pytest.importorskip("scipy")

from swingvision import calibration, court  # noqa: E402
from swingvision import courtfit as ad  # noqa: E402

_W, _H = 1280, 720
# elevated behind-baseline pose: (Cx, Cy, Cz, yaw, pitch, focal_px)
_POSE = (court.DOUBLES_WIDTH / 2.0, -6.0, 4.0, 0.0, 0.3, 1100.0)


def _physical_quad():
    q = ad._cam_corners(_POSE, _W, _H, court)
    assert q is not None
    return {k: [float(v[0]), float(v[1])] for k, v in q.items()}


def test_physical_quad_passes_through():
    q = _physical_quad()
    res = ad.cam_fit_quad(q, calibration, court, _W, _H)
    assert res is not None
    _, locked, fit_px, cam = res
    assert fit_px < 1.0
    assert cam[5] > 0          # a real focal length rides along
    for k in ad.DBL:
        assert abs(locked[k][0] - q[k][0]) < 3.0
        assert abs(locked[k][1] - q[k][1]) < 3.0


def test_impossible_quad_is_corrected_to_a_legal_shape():
    q = _physical_quad()
    q["far_bl_doubles"][0] += 90.0   # a skew no camera view of a court produces
    q["far_bl_doubles"][1] += 40.0
    res = ad.cam_fit_quad(q, calibration, court, _W, _H)
    assert res is not None
    _, locked, fit_px = res[:3]
    assert fit_px > 8.0              # the distortion was recognised, not kept
    res2 = ad.cam_fit_quad(locked, calibration, court, _W, _H)
    assert res2 is not None
    assert res2[2] < 1.5             # the output itself is a real camera shape


# A mildly ROLLED camera (phone on a fence/tripod is only roughly level; a real
# clip measured -1.1deg): (Cx, Cy, Cz, yaw, pitch, focal_px, roll_rad).
_ROLLED_POSE = (court.DOUBLES_WIDTH / 2.0, -6.0, 4.0, 0.0, 0.3, 1100.0,
                math.radians(2.5))


def _rolled_quad():
    q = ad._cam_corners(_ROLLED_POSE, _W, _H, court)
    assert q is not None
    return {k: [float(v[0]), float(v[1])] for k, v in q.items()}


def _mean_corner_err(a, b):
    return float(np.mean([math.hypot(a[k][0] - b[k][0], a[k][1] - b[k][1])
                          for k in ad.DBL]))


def test_trusted_lock_keeps_camera_roll():
    """The overlay tool / pipeline lock is the TRUSTED path (allow_roll=True): a
    real camera with a few degrees of mounting roll must be reproduced, not
    flattened to roll=0. The roll-FROZEN candidate lock cannot express the roll,
    so it drags the whole court off the true (on-paint) corners - exactly the
    'corners are close but Snap won't lock onto the lines' bug on rolled clips.
    """
    q = _rolled_quad()   # the true, on-paint corners of a rolled camera
    frozen, _m0, _f0 = ad.lock_quad(dict(q), calibration, court, _W, _H,
                                    allow_roll=False)
    rolled, _m1, _f1 = ad.lock_quad(dict(q), calibration, court, _W, _H,
                                    allow_roll=True)
    e_rolled = _mean_corner_err(rolled, q)
    e_frozen = _mean_corner_err(frozen, q)
    assert e_rolled < 1.5                 # roll expressed -> stays on the paint
    assert e_frozen > 3.0                 # roll=0 cannot fit a rolled court
    assert e_rolled < e_frozen / 3.0      # a large win, not a marginal one
