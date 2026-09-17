"""Calibration: the homography solve recovers a synthetic camera, and
reprojection error of the named landmarks stays well under the ~5 px bar."""

import numpy as np

from swingvision import calibration, court


def _true_homography():
    """Pick an arbitrary, well-conditioned 'true' camera homography, mapping
    court metres to a 1920x1080 image with a behind-the-baseline perspective."""
    court_corners = [
        court.LANDMARKS["near_bl_doubles"],
        court.LANDMARKS["near_br_doubles"],
        court.LANDMARKS["far_bl_doubles"],
        court.LANDMARKS["far_br_doubles"],
    ]
    image_corners = [
        (305.0, 995.0),
        (1615.0, 1005.0),
        (758.0, 302.0),
        (1162.0, 298.0),
    ]
    return calibration.compute_homography(court_corners, image_corners)


def test_synthetic_camera_round_trip():
    H_true = _true_homography()

    names = court.landmark_names()
    court_pts = [court.LANDMARKS[n] for n in names]
    # Project every landmark through the true camera to get "observed" pixels.
    image_pts = calibration.court_to_image(H_true, court_pts)

    # Recover the homography from all 14 correspondences.
    H_rec = calibration.compute_homography(court_pts, image_pts)

    # Recovered H should reproduce the same pixels.
    err = calibration.reprojection_error(H_rec, court_pts, image_pts)
    assert err < 1e-6

    # And it should match the true homography (both normalized H[2,2]=1).
    assert np.allclose(H_rec, H_true, atol=1e-6)


def test_reprojection_error_under_threshold_with_noise():
    H_true = _true_homography()
    names = court.landmark_names()
    court_pts = [court.LANDMARKS[n] for n in names]
    image_pts = calibration.court_to_image(H_true, court_pts)

    # Add sub-pixel click noise, as a manual calibration would have.
    rng = np.random.default_rng(0)
    noisy = image_pts + rng.normal(scale=0.5, size=image_pts.shape)

    H = calibration.compute_homography(court_pts, noisy)
    err = calibration.reprojection_error(H, court_pts, noisy)
    assert err < 5.0, f"reprojection error {err:.2f}px exceeds 5px"


def test_homography_from_named_landmarks():
    H_true = _true_homography()
    names = court.landmark_names()
    image_pts = calibration.court_to_image(H_true, [court.LANDMARKS[n] for n in names])
    named = {n: list(px) for n, px in zip(names, image_pts)}

    H = calibration.homography_from_landmarks(named)
    assert np.allclose(H, H_true, atol=1e-6)


def test_needs_four_points():
    try:
        calibration.compute_homography([(0, 0), (1, 0), (0, 1)], [(0, 0), (1, 0), (0, 1)])
    except ValueError:
        return
    raise AssertionError("expected ValueError for fewer than 4 correspondences")


def _camera_homography(f, img_w, img_h, cam_pos, target):
    """Ground-truth plane homography for a pinhole camera at cam_pos looking at
    target (both in court metres, z up), square pixels, centred principal point."""
    K = np.array([[f, 0, img_w / 2.0], [0, f, img_h / 2.0], [0, 0, 1.0]])
    cam_pos = np.asarray(cam_pos, float)
    fwd = np.asarray(target, float) - cam_pos
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    down = np.cross(fwd, right)
    R = np.stack([right, down, fwd])          # world -> camera axes (x right, y down, z fwd)
    t = -R @ cam_pos
    return K @ np.column_stack([R[:, 0], R[:, 1], t])


def test_focal_self_calibration_recovers_f():
    # A baseline camera 6 m up behind the court, 1000 px focal on 1280x720.
    H = _camera_homography(1000.0, 1280, 720,
                           cam_pos=(court.DOUBLES_WIDTH / 2, -8.0, 6.0),
                           target=(court.DOUBLES_WIDTH / 2, court.NET_Y, 0.0))
    f = calibration.focal_from_homography(H, (1280, 720))
    assert f is not None
    assert abs(f - 1000.0) / 1000.0 < 0.02, f"recovered {f:.0f}px, want ~1000px"


def test_focal_self_calibration_wide_lens():
    # A phone-like wide lens (short focal) from a lower mount.
    H = _camera_homography(700.0, 1280, 720,
                           cam_pos=(court.DOUBLES_WIDTH / 2 + 2.0, -5.0, 4.0),
                           target=(court.DOUBLES_WIDTH / 2, court.NET_Y, 0.0))
    f = calibration.focal_from_homography(H, (1280, 720))
    assert f is not None
    assert abs(f - 700.0) / 700.0 < 0.02, f"recovered {f:.0f}px, want ~700px"


def test_broadcast_court_detector_and_coverage():
    """PRO profile court auto-calibration: from a generic broadcast seed, the
    line-snap recovers a synthetic court, and line_coverage separates a good fit
    from a skewed one (the accept/refuse gate)."""
    import cv2
    import numpy as np

    from swingvision import court

    w, h = 1280, 720
    corners = {"near_bl_doubles": [150, 660], "near_br_doubles": [1130, 655],
               "far_bl_doubles": [360, 250], "far_br_doubles": [970, 248]}
    names = list(corners)
    H_true = calibration.compute_homography(
        [court.LANDMARKS[n] for n in names], [corners[n] for n in names])
    img = np.full((h, w, 3), 100, np.uint8)
    for a, b in court.LINES:
        p = calibration.court_to_image(H_true, [a])[0]
        q = calibration.court_to_image(H_true, [b])[0]
        cv2.line(img, (int(p[0]), int(p[1])), (int(q[0]), int(q[1])), (255, 255, 255), 2)

    skew = H_true @ np.array([[1, 0.15, 0], [0, 1, 0], [0, 0, 1.0]])
    assert calibration.line_coverage(img, H_true, tol_px=5) > 0.6
    assert calibration.line_coverage(img, skew, tol_px=5) < 0.5

    det = calibration.detect_court_broadcast(img)
    assert det is not None, "should recover the synthetic broadcast court"
    assert det.confidence > 0.6
    # recovered corners land near the truth
    for n in names:
        gx, gy = calibration.court_to_image(det.homography, [court.LANDMARKS[n]])[0]
        assert np.hypot(gx - corners[n][0], gy - corners[n][1]) < 25
