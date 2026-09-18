"""Pins the new logic in tools/court_cost_separation.py (evidence section G7):
the RIDGE RESIDUAL instrument and the threshold/split/verdict arithmetic the G7
verdict is read off. Nothing here renders a court - the ridge tests splat bright
blobs exactly where a camera puts its paint samples, so "the right camera" and
"a dolly-zoomed camera" are both exactly known."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

S = pytest.importorskip("court_cost_separation")
T = pytest.importorskip("court_fit_cp1")
camera3d = pytest.importorskip("swingvision.camera3d")


def _image_of(cam, amp=120.0, sig=1.2):
    """A grey image with a bright Gaussian blob at every paint sample `cam`
    projects into the frame: the image for which `cam` is exactly right."""
    w, h = cam.image_wh
    img = np.full((h, w), 40.0)
    world, _, _, _, _ = camera3d._samples(S.RIDGE_STEP_M)
    uv = cam.project(world)
    uv = uv[np.isfinite(uv).all(1)]
    uv = uv[(uv[:, 0] >= 4) & (uv[:, 0] < w - 4) & (uv[:, 1] >= 4) & (uv[:, 1] < h - 4)]
    yy, xx = np.mgrid[-3:4, -3:4]
    ker = amp * np.exp(-(xx ** 2 + yy ** 2) / (2 * sig ** 2))
    for u, v in uv:
        c, r = int(round(u)), int(round(v))
        img[r - 3:r + 4, c - 3:c + 4] += ker
    return np.clip(img, 0, 255).astype(np.uint8)


@pytest.fixture(scope="module")
def true_cam():
    rcam, _, _ = T.truth_camera(distortion=True)
    return camera3d.CourtCamera.from_paintfit(rcam, "truth")


def test_ridge_residual_is_near_zero_for_the_camera_that_drew_the_image(true_cam):
    r = S.ridge_residual(_image_of(true_cam), true_cam)
    assert r["n"] > 200
    assert r["found"] > 0.99                    # every sample has a ridge
    assert r["med"] < 0.2 and r["mean"] < 0.3   # px @720


def test_ridge_residual_grows_and_censors_for_a_dolly_zoomed_camera(true_cam):
    img = _image_of(true_cam)
    good = S.ridge_residual(img, true_cam)
    bad = S.ridge_residual(img, camera3d.dolly_zoom(true_cam, 1.15))
    assert bad["mean"] > 10 * good["mean"]
    assert bad["found"] < good["found"]
    # censoring: no residual may exceed the reach, and a miss scores exactly it
    assert bad["mean"] <= S.RIDGE_REACH_PX_720 + 1e-9
    assert bad["med"] <= S.RIDGE_REACH_PX_720 + 1e-9


def test_ridge_residual_shares_paint_checks_far_line_blind_spot(true_cam):
    """Declared in G7: the width filter hides the far lines from BOTH
    instruments, so neither judges a camera on them."""
    chk = camera3d.paint_check(_image_of(true_cam), true_cam)
    assert "far_baseline" in chk.unchecked and "far_service" in chk.unchecked
    assert S.RIDGE_MIN_WIDTH_PX_720 == 0.67     # paint_check's own value


def test_wrong_label_comes_from_the_fitted_focal_not_from_truth():
    ft = S.f_true()
    rows = [{"f_fit": ft}, {"f_fit": ft * 1.005}, {"f_fit": ft * 1.02}, {"f_fit": ft * 0.5}]
    assert list(S.label_wrong(rows)) == [False, False, True, True]
    assert abs(ft - (1920 / 2) / math.tan(math.radians(100) / 2)) < 1e-9


def test_threshold_at_catch_is_the_tightest_threshold_reaching_the_target():
    score = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])
    wrong = np.array([False] * 5 + [True] * 5)
    t = S._threshold_at_catch(score, wrong, 0.80)       # 4 of 5 wrong
    assert t == 6.0
    assert S._rates(score, wrong, t) == (0.8, 0.0)
    t = S._threshold_at_catch(score, wrong, 1.00)
    assert t == 5.0 and S._rates(score, wrong, t) == (1.0, 0.0)
    assert S._threshold_at_catch(score, np.zeros(10, bool), 0.9) is None


def test_oriented_flips_low_means_wrong_and_sends_non_finite_to_the_wrong_end():
    v = [0.9, 0.5, float("nan")]
    o = S._oriented(v, -1)
    assert o[1] > o[0]                       # a lower support scores MORE wrong
    assert o[2] > o[1]                       # an unmeasurable camera is maximally wrong
    assert np.isfinite(o).all()


def test_split_is_stratified_and_seeded():
    wrong = np.array([True] * 33 + [False] * 365)
    a = S._split(len(wrong), wrong, 0)
    assert np.array_equal(a, S._split(len(wrong), wrong, 0))
    assert not np.array_equal(a, S._split(len(wrong), wrong, 1))
    assert int((a & wrong).sum()) == 16 and int((~a & wrong).sum()) == 17
    assert int((a & ~wrong).sum()) == 182


def test_verdict_matches_the_pre_registered_bar():
    assert S.verdict(0.95, 0.01) == "SEPARATES"
    assert S.verdict(0.95, 0.05) == "PARTIAL"
    assert S.verdict(0.95, 0.20) == "FAILS"
    assert S.verdict(0.50, 0.12) == "FAILS"
