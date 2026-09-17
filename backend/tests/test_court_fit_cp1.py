"""Pins tools/court_fit_cp1.py (CP1 stage 1): the renderer, the profile model and
the seeded whole-court fit (R1).

The two end-to-end tests render a full 1080p court (about 2 minutes the first
time; cached under data/output/court_fit_cp1/cache afterwards)."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

T = pytest.importorskip("court_fit_cp1")
C1 = pytest.importorskip("court_map_ceiling")


def test_truth_camera_is_c1s_camera():
    cam, kp, pitch = T.truth_camera(distortion=False)
    pr = C1.true_projector(3.0, pitch, 100.0)
    xy = np.random.default_rng(0).uniform([0, 0], [11, 24], (50, 2))
    assert np.abs(cam.project_ground(xy) - pr(xy)).max() < 1e-9
    assert np.abs(cam.ground(cam.project_ground(xy)) - xy).max() < 1e-9


def test_lens_models_round_trip_and_brown_is_about_30px_at_the_edge():
    cam, _, _ = T.truth_camera(distortion=True)
    uv = np.random.default_rng(1).uniform([0, 0], [1920, 1080], (200, 2))
    assert np.abs(cam.distort(cam.undistort(uv)) - uv).max() < 1e-6
    edge = cam.distort(np.array([[1919.5, 540.0]]))[0, 0] - 1919.5
    assert edge == pytest.approx(-30.0, abs=0.5)
    div = T.Camera.from_params(np.append(cam.params()[:7], -0.04))
    assert np.abs(div.undistort(div.distort(uv)) - uv).max() < 1e-6


def test_seed_from_exact_corners_is_the_exact_camera():
    cam, _, _ = T.truth_camera(distortion=False)
    corners = {n: cam.project_ground([T.CT.LANDMARKS[n]])[0] for n in T.CORNERS}
    s = T.seed_camera(corners)
    assert np.allclose(s.params()[:7], cam.params()[:7], atol=1e-6)


def test_blurred_step_model():
    x = np.linspace(-6, 6, 241)
    for b1, b2 in ((0.05, 1.0), (0.6, 0.8)):
        F = T._F(x, 0.9, b1, b2)
        assert T._F(np.array([0.0]), 0.9, b1, b2)[0] == pytest.approx(0.5, abs=1e-12)
        assert np.all(np.diff(F) >= -1e-12) and F[0] < 1e-6 and F[-1] > 1 - 1e-6
        num = (T._F(x + 1e-5, 0.9, b1, b2) - T._F(x - 1e-5, 0.9, b1, b2)) / 2e-5
        assert np.abs(num - T._Fd(x, 0.9, b1, b2)).max() < 1e-6


def test_step_basis_puts_the_court_side_at_one_for_both_orientations():
    """kappa is only one number if the step always rises INTO the court."""
    d = np.array([-5.0, 5.0])
    edges = (np.full(2, -0.5), np.full(2, 0.5))
    for outer in (-1, 1):
        cols, _ = T._design(d, edges, outer, 1.0, 0.05, 1.0, "step", None, None, False)
        step = cols[2]
        court_side = 0 if outer > 0 else 1        # run-off lies on the +outer side
        assert step[court_side] == pytest.approx(1.0, abs=1e-4)
        assert step[1 - court_side] == pytest.approx(0.0, abs=1e-4)


def test_blurring_after_pixel_binning_erases_subpixel_position():
    """Why the renderer applies the PSF BEFORE pixel integration (a deviation
    from the literal order in court-precision-routes.md s7): a band narrower than
    a pixel, moved inside its pixel row, is invisible to the literal order."""
    from scipy import ndimage
    fine = 64
    x = (np.arange(40 * fine) + 0.5) / fine

    def band(c):
        return ((x > c - 0.07) & (x < c + 0.07)).astype(float)

    def literal(c):         # bin to pixels, then blur
        return ndimage.gaussian_filter1d(band(c).reshape(40, fine).mean(1), 1.0)

    def optics_first(c):    # blur, then bin
        return ndimage.gaussian_filter1d(band(c), fine * 1.0).reshape(40, fine).mean(1)
    assert np.abs(literal(20.3) - literal(20.6)).max() < 1e-12
    assert np.abs(optics_first(20.3) - optics_first(20.6)).max() > 1e-3


@pytest.fixture(scope="module")
def ctl1_row():
    return T.run_trial({"arm": "ctl1", "trial": 0, "seed": 7})


def test_control1_reproduces_exact_geometry(ctl1_row):
    """Zero noise, zero distortion, exact corners: every line, both readouts,
    well under the 5 mm control bar, and the camera height recovered."""
    r = ctl1_row
    assert r["ok"], r.get("error")
    for name, v in r["lines"].items():
        assert v["M"] < 0.005, (name, v)
        assert v["L"] < 0.005, (name, v)
    assert r["cam_h"] == pytest.approx(3.0, abs=1e-3)
    assert r["f_fit"] == pytest.approx(C1.W / 2 / math.tan(math.radians(50)), abs=0.5)


def test_a_010px_vertical_shift_is_recovered_on_the_far_baseline():
    r = T.run_trial({"arm": "ctl3a", "trial": 0, "seed": 7})
    assert r["ok"], r.get("error")
    assert r["far_bl"]["L_offset_px"] == pytest.approx(0.10, abs=0.02)
