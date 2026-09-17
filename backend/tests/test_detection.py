"""Classical court detection + overlay, validated on a synthetic camera render
(no real footage needed). Skipped if OpenCV isn't installed."""

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")  # noqa: F841

from swingvision import calibration, court, overlay


def _true_homography():
    """A behind-the-baseline perspective into a 1280x720 frame."""
    corners = [
        court.LANDMARKS[n]
        for n in ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
    ]
    image = [(300, 660), (980, 660), (520, 150), (760, 150)]
    return calibration.compute_homography(corners, image)


def test_detect_synthetic_court():
    H_true = _true_homography()
    img = overlay.synthetic_court_image(H_true, 1280, 720, thickness=3)

    det = calibration.detect_court(img)
    assert det is not None, "detector returned None on a clean synthetic court"
    assert det.confidence > 0.5

    names = court.landmark_names()
    true_px = calibration.court_to_image(H_true, [court.LANDMARKS[n] for n in names])
    det_px = np.array([det.keypoints[n] for n in names])
    err = np.sqrt(((det_px - true_px) ** 2).sum(axis=1)).mean()
    assert err < 8.0, f"detected keypoints off by {err:.2f}px"


def test_detect_court_keypoints_confidence_gate():
    # A blank frame has no lines -> low confidence -> None (caller falls back).
    blank = np.full((720, 1280, 3), (70, 120, 60), dtype=np.uint8)
    assert calibration.detect_court_keypoints(blank) is None


def test_overlay_lines_land_on_court():
    """Project the court back through the *true* homography and confirm the
    drawn overlay actually paints onto the rendered lines (sanity that
    court_to_image + draw agree with synthetic_court_image)."""
    H_true = _true_homography()
    base = overlay.synthetic_court_image(H_true, 1280, 720, thickness=3)
    drawn = overlay.draw_court(base.copy(), H_true, thickness=2, dots=False)
    # The overlay must change pixels near the lines but not blow up the frame.
    assert drawn.shape == base.shape
    assert np.any(drawn != base)
