"""The tracking sim's run-off step (job 1, 2026-09-23).

Every tracking number up to G9 was measured with the whole ground one brightness.
The run-off step is opt-in; these pin that the default scene did not move, and that
the step lands where CP1 puts it (the outer edge of the outer lines' paint)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
S = pytest.importorskip("court_track_sim")

from swingvision import court  # noqa: E402

WH = (640, 360)


@pytest.fixture(scope="module")
def cam():
    return S.camera(0.0, S.base_pitch(WH), 0.0, wh=WH)


def test_the_default_is_no_runoff_step():
    assert S.RUNOFF_DN_DEFAULT is None


@pytest.mark.parametrize("subpixel", [False, True])
def test_runoff_at_the_surface_brightness_is_bit_identical_to_no_runoff(cam, subpixel):
    # Same random draws, same image: the new branch touches only run-off pixels.
    a = S.render(cam, np.random.default_rng(7), subpixel=subpixel)
    b = S.render(cam, np.random.default_rng(7), subpixel=subpixel, runoff_dn=S.SURFACE_DN)
    assert np.array_equal(a, b)


def test_the_runoff_step_draws_no_random_numbers(cam):
    r1, r2 = np.random.default_rng(3), np.random.default_rng(3)
    S.render(cam, r1, subpixel=True)
    S.render(cam, r2, subpixel=True, runoff_dn=S.RUNOFF_DN_CP1)
    assert r1.random() == r2.random()


def test_the_runoff_is_outside_the_court_and_the_court_is_not(cam):
    img = S.render(cam, np.random.default_rng(0), noise=False, runoff_dn=S.RUNOFF_DN_CP1)
    xm = court.X_CENTER + 1.3          # clear of the centre mark
    pts = {"court, 2 m inside the far baseline": ((xm, court.Y_FAR_BASELINE - 2.0, 0), 95.0),
           "run-off, 2 m past the far baseline": ((xm, court.Y_FAR_BASELINE + 2.0, 0), 80.0),
           "run-off, 1 m behind the near baseline": ((xm, court.Y_NEAR_BASELINE - 1.0, 0), 80.0),
           "run-off, 1 m outside the left sideline": ((court.X_LEFT_DOUBLES - 1.0, 6.0, 0), 80.0)}
    for what, (p, dn) in pts.items():
        u, v = cam.project(np.array([p], float))[0]
        assert 0 <= u < WH[0] and 0 <= v < WH[1], what
        assert abs(img[int(round(v)), int(round(u))] - dn) < 1.0, what
