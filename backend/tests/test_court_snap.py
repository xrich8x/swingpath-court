"""Guarded line-snap (calibration.snap_to_lines).

Synthetic court: render the rigid template through a known homography, jitter the
corners to imitate rough clicks, and check the snap pulls them back onto the lines.
The guard must REFUSE when there are no visible lines (returns the input unchanged).
"""

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from swingvision import calibration, court

_DBL = ("near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles")
_TRUE_IMG = {  # a plausible behind-baseline trapezoid in a 640x360 frame
    "near_bl_doubles": [150.0, 330.0], "near_br_doubles": [490.0, 330.0],
    "far_br_doubles": [400.0, 90.0], "far_bl_doubles": [240.0, 90.0],
}


def _render_court(H, w=640, h=360):
    """Draw the court's line SEGMENTS (not dots) so line_ridge_mask sees ridges."""
    frame = np.zeros((h, w, 3), np.uint8)
    for a, b in court.LINES:
        pa = calibration.court_to_image(H, [a])[0]
        pb = calibration.court_to_image(H, [b])[0]
        cv2.line(frame, (int(round(pa[0])), int(round(pa[1]))),
                 (int(round(pb[0])), int(round(pb[1]))), (255, 255, 255), 2)
    return frame


def _mean_corner_err(named):
    return float(np.mean([np.hypot(named[n][0] - _TRUE_IMG[n][0],
                                   named[n][1] - _TRUE_IMG[n][1]) for n in _DBL]))


def test_snap_pulls_rough_corners_onto_lines():
    court_pts = [court.LANDMARKS[n] for n in _DBL]
    H_true = calibration.compute_homography(court_pts, [_TRUE_IMG[n] for n in _DBL])
    frame = _render_court(H_true)

    rng = np.random.default_rng(0)
    rough = {n: [_TRUE_IMG[n][0] + float(rng.uniform(-8, 8)),
                 _TRUE_IMG[n][1] + float(rng.uniform(-8, 8))] for n in _DBL}

    H, out, snapped, cov0, cov1 = calibration.snap_to_lines(frame, rough)
    assert snapped is True
    assert cov1 >= cov0                       # never lowers coverage
    assert _mean_corner_err(out) < _mean_corner_err(rough)   # closer to truth


def test_snap_refused_without_visible_lines():
    blank = np.zeros((360, 640, 3), np.uint8)
    rough = dict(_TRUE_IMG)
    H, out, snapped, cov0, cov1 = calibration.snap_to_lines(blank, rough)
    assert snapped is False          # no lines to clear the coverage bar
    assert out is rough              # input returned unchanged (safe fallback)


def test_snap_skipped_when_corners_missing():
    blank = np.zeros((360, 640, 3), np.uint8)
    partial = {n: _TRUE_IMG[n] for n in _DBL[:3]}   # only 3 of 4 corners
    H, out, snapped, cov0, cov1 = calibration.snap_to_lines(blank, partial)
    assert snapped is False
    assert out is partial


def test_snap_court_clay_retry():
    """Colour-tinted (clay) lines: the white path refuses (saturated paint is
    invisible to line_ridge_mask's sat gate), the clay retry snaps instead."""
    from swingvision import courtfit

    court_pts = [court.LANDMARKS[n] for n in _DBL]
    H_true = calibration.compute_homography(court_pts, [_TRUE_IMG[n] for n in _DBL])
    frame = np.full((360, 640, 3), (110, 60, 40), np.uint8)   # dark clay ground
    for a, b in court.LINES:
        pa = calibration.court_to_image(H_true, [a])[0]
        pb = calibration.court_to_image(H_true, [b])[0]
        cv2.line(frame, (int(round(pa[0])), int(round(pa[1]))),
                 (int(round(pb[0])), int(round(pb[1]))), (60, 140, 235), 2)

    rng = np.random.default_rng(5)
    rough = {n: [_TRUE_IMG[n][0] + float(rng.uniform(-9, 9)),
                 _TRUE_IMG[n][1] + float(rng.uniform(-9, 9))] for n in _DBL}

    _H, out, snapped, tag, cov = courtfit.snap_court(frame, rough, calibration, court)
    assert snapped is True
    assert tag == "snap-clay"
    assert _mean_corner_err(out) < _mean_corner_err(rough)
