"""The step-aware far-line check (job 2, 2026-09-23): the paint fit's own
paint+step model, read at the camera's prediction of each far line.

Scene: the tracking sim at 1080p WITH CP1's run-off step - the scene on which
every ridge-finder reads the far baseline ~1 px off. Truth is the camera that
rendered it."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
S = pytest.importorskip("court_track_sim")

from swingvision import camera3d  # noqa: E402


@pytest.fixture(scope="module")
def scene():
    p0 = S.base_pitch()
    cam = S.camera(0.0, p0, 0.0)
    img = np.clip(S.render(cam, np.random.default_rng(11), subpixel=True,
                           runoff_dn=S.RUNOFF_DN_CP1), 0, 255).astype(np.uint8)
    return img, cam, p0


@pytest.fixture(scope="module")
def true_meas(scene):
    img, cam, _ = scene
    return camera3d.far_line_stepfit_measure(img, cam)


def test_the_default_is_unchanged():
    assert camera3d.FAR_MODE_DEFAULT == "stack"
    assert camera3d.FAR_LINES_DEFAULT is False


def test_the_run_off_step_is_measured_as_kappa(true_meas):
    # kappa = paint / (surface - run-off) = 110 / ~16: the step was SEEN, so the
    # far baseline is fitted with the step tied to its outer edge
    assert true_meas["kappa"] is not None and 5.0 < true_meas["kappa"] < 10.0


def test_the_true_camera_reads_on_the_far_lines_despite_the_step(scene, true_meas):
    img, cam, _ = scene
    sc = camera3d.score_stepfit(true_meas, far_tol_px_720=0.35, s_scale=1.5)
    for nm in camera3d.FAR_LINES:
        assert sc[nm]["seen"], nm
        assert sc[nm]["frac"] >= 0.5, (nm, sc[nm])
    assert sc["far_baseline"]["mode"] == "kappa"
    # the stacked ridge reads this line ~+1 px off (job 1); the model reads it on
    assert np.median(np.abs(sc["far_baseline"]["off"])) < 0.3


def test_a_wrong_far_line_is_a_measured_miss(scene):
    img, cam, p0 = scene
    wrong = S.camera(0.0, p0 + math.radians(0.05), 0.0)      # far lines ~26 cm out
    sc = camera3d.far_line_stepfit(img, wrong, far_tol_px_720=0.35)
    assert sc["far_baseline"]["seen"] and sc["far_baseline"]["frac"] < 0.5


def test_a_fit_at_the_window_edge_is_a_MISS_not_unseen():
    # G8 bar 3's failure: a far ridge that falls out of view left the denominator.
    meas = {"lines": {"far_baseline": {"c": [0.0, 4.48, 0.0, 4.48], "sig_c": [0.05, 9.0, 0.05, 9.0],
                                       "sigf": [100.0] * 4, "amp": [1.0] * 4,
                                       "win": [4.5] * 4, "mode": "kappa", "n_try": 4}}}
    sc = camera3d.score_stepfit(meas, far_tol_px_720=0.35, s_scale=1.5)["far_baseline"]
    assert sc["class"] == ["hit", "miss", "hit", "miss"]
    assert sc["frac"] == 0.5 and sc["n_det"] == 4


def test_no_signal_is_unseen_and_not_evidence():
    meas = {"lines": {"far_service": {"c": [0.1, 0.2], "sig_c": [0.05, 0.05],
                                      "sigf": [3.0, 3.0], "amp": [1.0, 1.0],
                                      "win": [4.5, 4.5], "mode": "free", "n_try": 2}}}
    sc = camera3d.score_stepfit(meas, s_scale=1.5)["far_service"]
    assert not sc["seen"] and sc["n_det"] == 0


def test_paint_check_stepfit_checks_the_whole_court(scene):
    img, cam, _ = scene
    c = camera3d.paint_check(img, cam, far_lines=True, far_mode="stepfit",
                             far_kw={"far_tol_px_720": 0.35})
    assert c.ok and c.scope == "whole_court" and not c.unchecked


def test_a_pre_scored_far_dict_gives_the_same_check(scene, true_meas):
    img, cam, _ = scene
    sc = camera3d.score_stepfit(true_meas, far_tol_px_720=0.35, s_scale=1.5)
    a = camera3d.paint_check(img, cam, far_lines=True, far_scored=sc)
    b = camera3d.paint_check(img, cam, far_lines=True, far_mode="stepfit",
                             far_kw={"far_tol_px_720": 0.35})
    assert a.ok == b.ok and a.lines == b.lines


def test_an_unknown_far_mode_is_refused(scene):
    img, cam, _ = scene
    with pytest.raises(ValueError):
        camera3d.paint_check(img, cam, far_lines=True, far_mode="pyramid")
