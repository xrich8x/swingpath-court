"""The 3D keypoints and the collinear sets are regulation geometry, derived from
the 2D constants rather than retyped."""
import itertools

import numpy as np
import pytest

from swingvision import calibration, court, courtfit


def test_ground_keypoints_are_the_2d_landmarks_at_z0():
    for name, (x, y) in court.LANDMARKS.items():
        assert court.LANDMARKS_3D[name] == (x, y, 0.0)


def test_net_structure_heights_and_offsets():
    L3 = court.LANDMARKS_3D
    assert L3["net_post_left_top"] == (court.X_LEFT_POST, court.NET_Y, 1.07)
    assert L3["net_post_right_top"] == (court.X_RIGHT_POST, court.NET_Y, 1.07)
    assert L3["net_center_top"] == (court.X_CENTER, court.NET_Y, 0.914)
    assert court.X_RIGHT_POST - court.X_RIGHT_DOUBLES == pytest.approx(0.914)
    for side in ("left", "right"):
        base = L3[f"net_post_{side}_base"]
        assert base[:2] == court.NET_POST_BASES[f"net_post_{side}"] and base[2] == 0.0


def test_keypoint_order_is_stable_and_complete():
    assert court.KEYPOINTS_3D == tuple(court.LANDMARKS_3D)
    assert len(court.KEYPOINTS_3D) == 21
    assert court.KEYPOINTS_3D[:14] == tuple(court.LANDMARKS)


@pytest.mark.parametrize("line", sorted(court.COLLINEAR_SETS))
def test_collinear_sets_are_collinear_and_ordered(line):
    pts = np.array([court.LANDMARKS_3D[n] for n in court.COLLINEAR_SETS[line]])
    axis = 0 if line.endswith("baseline") else 1
    other = 1 - axis
    assert np.ptp(pts[:, other]) == 0 and np.all(pts[:, 2] == 0)
    assert np.all(np.diff(pts[:, axis]) > 0)


def test_cross_ratio_of_the_baseline_is_the_regulation_value():
    # doubles-L, singles-L, singles-R, doubles-R
    xs = (0.0, 1.37, 9.60, 10.97)
    expected = ((9.60 - 0.0) * (10.97 - 1.37)) / ((9.60 - 1.37) * (10.97 - 0.0))
    assert courtfit.cross_ratio(*xs) == pytest.approx(expected)


def test_cross_ratio_survives_a_projective_map():
    """Any homography of the court plane leaves every 4-point cross-ratio alone."""
    rng = np.random.default_rng(3)
    for _ in range(20):
        H = np.eye(3) + rng.normal(0, 0.2, (3, 3))
        H[2, :2] = rng.normal(0, 0.02, 2)
        for line, names in court.COLLINEAR_SETS.items():
            axis = 0 if line.endswith("baseline") else 1
            ground = [court.LANDMARKS_3D[n][:2] for n in names]
            img = calibration.court_to_image(H, ground)
            if not np.all(np.isfinite(img)):
                continue
            along, _ = courtfit._line_coords(img)
            if along[-1] < along[0]:
                along = -along
            for sub in itertools.combinations(range(len(names)), 4):
                world = [ground[i][axis] for i in sub]
                a = along[list(sub)]
                if not np.all(np.diff(a) > 0):     # the map folded the line (behind camera)
                    continue
                assert courtfit.cross_ratio(*a) == pytest.approx(courtfit.cross_ratio(*world),
                                                                rel=1e-6)
