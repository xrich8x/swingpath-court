"""Court geometry: constants, membership tests, and the image<->court inverse
property of the projection."""

import numpy as np

from swingvision import calibration, court


def test_court_dimensions():
    assert court.LENGTH == 23.77
    assert court.DOUBLES_WIDTH == 10.97
    # Singles width is doubles minus two alleys.
    assert abs((court.X_RIGHT_SINGLES - court.X_LEFT_SINGLES) - court.SINGLES_WIDTH) < 1e-9
    # Service lines sit 6.40 m either side of the net.
    assert abs(court.NET_Y - court.Y_NEAR_SERVICE - court.SERVICE_LINE_FROM_NET) < 1e-9
    assert abs(court.Y_FAR_SERVICE - court.NET_Y - court.SERVICE_LINE_FROM_NET) < 1e-9


def test_landmark_count_and_bounds():
    assert len(court.LANDMARKS) == 14
    for x, y in court.LANDMARKS.values():
        assert 0.0 <= x <= court.DOUBLES_WIDTH
        assert 0.0 <= y <= court.LENGTH


def test_membership():
    assert court.is_in_singles(5.0, 12.0)
    assert not court.is_in_singles(0.5, 12.0)        # in the doubles alley
    assert court.is_in_doubles(0.5, 12.0)
    assert not court.is_in_singles(5.0, 24.5)        # long, past the baseline
    # Margin gives the benefit of the doubt on the line.
    assert court.is_in_singles(court.X_RIGHT_SINGLES + 0.04, 12.0, margin=0.05)


def _synthetic_camera_homography():
    """A realistic behind-the-baseline perspective: build H from the four
    doubles corners mapped to an image trapezoid (near edge wider)."""
    court_corners = [
        court.LANDMARKS["near_bl_doubles"],
        court.LANDMARKS["near_br_doubles"],
        court.LANDMARKS["far_bl_doubles"],
        court.LANDMARKS["far_br_doubles"],
    ]
    image_corners = [
        (300.0, 1000.0),
        (1620.0, 1000.0),
        (760.0, 300.0),
        (1160.0, 300.0),
    ]
    return calibration.compute_homography(court_corners, image_corners)


def test_image_to_court_inverts_court_to_image():
    H = _synthetic_camera_homography()
    for name, pt in court.LANDMARKS.items():
        img = calibration.court_to_image(H, [pt])
        back = calibration.image_to_court(H, img)[0]
        assert np.allclose(back, pt, atol=1e-6), f"round trip failed at {name}"
