"""Rule 7: lifting the R1 fit from tools/court_fit_cp1.py into swingvision.paintfit
changed nothing.

The pinned values below were produced by the PRE-LIFT code (b3af0ca) on arm A3,
trial 0, seed 1: Brown lens rendered, fence and truss clutter, sensor noise,
30-frame mean - every stage of the fitter, tape model and kappa included - but no
video codec. Arm P is not pinned: libx265 is not deterministic run to run here
(two pre-lift runs of the same trial differ in bitrate and by up to 0.7 cm on the
far baseline), so a codec arm cannot be compared bit for bit
(docs/evidence/court-camera3d.md).

Renders the A3 court once (about 2 minutes without the cache)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

T = pytest.importorskip("court_fit_cp1")
from swingvision import camera3d, paintfit  # noqa: E402

PINNED_A3_T0_S1 = {
    "f_fit": 805.274377577432,
    "lam_fit": -0.051062014902715426,
    "cam_h": 3.0004828275993343,
    "kappa": 8.65581904171193,
    "sig_est": 1.15,
    "far_baseline_L": 0.011866459355502543,
    "far_baseline_M": 0.0038771119654690267,
    "far_service_L": 0.006219788817244021,
    "n_meas": {"near_baseline": 290, "far_baseline": 44, "doubles_L": 116, "doubles_R": 116,
               "singles_L": 84, "singles_R": 84, "near_service": 126, "far_service": 55,
               "centre_service": 19},
}


@pytest.fixture(scope="module")
def a3_row():
    return T.run_trial({"arm": "A3", "trial": 0, "seed": 1})


def test_a3_trial_reproduces_the_pre_lift_fit(a3_row):
    r, p = a3_row, PINNED_A3_T0_S1
    assert r["ok"], r.get("error")
    assert r["n_meas"] == p["n_meas"]
    for key in ("f_fit", "lam_fit", "cam_h", "kappa", "sig_est"):
        assert r[key] == pytest.approx(p[key], rel=1e-9, abs=1e-12), key
    assert r["lines"]["far_baseline"]["L"] == pytest.approx(p["far_baseline_L"], rel=1e-9)
    assert r["lines"]["far_baseline"]["M"] == pytest.approx(p["far_baseline_M"], rel=1e-9)
    assert r["lines"]["far_service_line"]["L"] == pytest.approx(p["far_service_L"], rel=1e-9)


def test_cp1_uses_the_production_fitter():
    assert T.r1_fit is paintfit.r1_fit
    assert T.FitConfig is paintfit.FitConfig
    assert issubclass(T.Camera, paintfit.Camera)


def test_division_normaliser_follows_the_image_size():
    a = paintfit.Camera((5, -6, 3), 0, 0.2, 0, 800, 960, 540, lam=-0.05, wh=(1920, 1080))
    b = paintfit.Camera((5, -6, 3), 0, 0.2, 0, 400, 480, 270, lam=-0.05, wh=(960, 540))
    assert a.hd == pytest.approx(2 * b.hd)
    uv = np.array([[100.0, 80.0], [1800.0, 1000.0]])
    assert np.allclose(a.distort(uv) / 2, b.distort(uv / 2))


def test_pose_only_fit_holds_focal_and_lens():
    """Tracking re-fits: start the R1 fit from a slightly wrong pose with the TRUE
    focal and lens held; the pose comes back, f and lam do not move."""
    cam, _, _ = T.truth_camera(distortion=True)
    cov = T._coverage_for(T.ARMS["A3"])
    img = T.clean_image(cov, 110.0, 0.9)
    ref = paintfit.Camera(cam.C, cam.yaw, cam.pitch, cam.roll, cam.f, cam.cx, cam.cy,
                          None, T.lam_star(cam), wh=(T.W, T.H))
    p = ref.params()
    off = paintfit.Camera.from_params(p + [0.05, -0.08, 0.03, 0.004, -0.003, 0.002, 0, 0],
                                      cam.cx, cam.cy, wh=(T.W, T.H))
    seed = camera3d.CourtCamera.from_paintfit(off, "test seed")
    fit = camera3d.fit_camera_on_paint(img, seed, pose_only=True).camera
    assert fit.f_px == seed.f_px and fit.dist == seed.dist
    assert fit.position_m() == pytest.approx(cam.C, abs=0.02)
