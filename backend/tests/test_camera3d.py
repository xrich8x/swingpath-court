"""camera3d: the CourtCamera model, the keypoint PnP seed, and the cross-ratio
outlier gate. Truth is a known synthetic camera throughout (rule 1): nothing
here is scored against a model's own output."""
import json
import math

import numpy as np
import pytest

from swingvision import camera3d as c3
from swingvision import court, courtfit, paintfit, setup_state

W, H = 1920, 1080


def make_cam(height=3.0, pitch=0.2, roll=0.0, hfov=100.0, yaw=0.03, setback=6.0,
             lens="none", dist=()):
    f = (W / 2) / math.tan(math.radians(hfov) / 2)
    brown = dist if lens == "brown" else None
    lam = dist[0] if lens == "division" else 0.0
    pf = paintfit.Camera((court.X_CENTER + 0.7, -setback, height), yaw, pitch, roll, f,
                         W / 2, H / 2, brown, lam, wh=(W, H))
    return c3.CourtCamera.from_paintfit(pf, "synthetic truth")


def visible_keypoints(cam):
    names = list(court.LANDMARKS_3D)
    uv = cam.project([court.LANDMARKS_3D[n] for n in names])
    return {n: tuple(p) for n, p in zip(names, uv)
            if np.isfinite(p).all() and 0 <= p[0] < W and 0 <= p[1] < H}


CAMS = [dict(height=1.5, pitch=0.10), dict(height=3.0, pitch=0.2, roll=0.02),
        dict(height=8.0, pitch=0.35, roll=-0.03, hfov=70.0)]


# ------------------------------------------------------------ the model -----
def test_opencv_convention_matches_projectpoints():
    import cv2
    cam = make_cam()
    X = np.random.default_rng(0).uniform([0, 0, 0], [11, 24, 2], (40, 3))
    ref, _ = cv2.projectPoints(X, cam.rvec, cam.tvec, cam.K, None)
    assert np.abs(cam.project(X) - ref.reshape(-1, 2)).max() < 1e-8


def test_position_and_hfov():
    cam = make_cam(height=3.0, hfov=100.0)
    assert cam.position_m() == pytest.approx([court.X_CENTER + 0.7, -6.0, 3.0], abs=1e-9)
    assert cam.hfov_deg() == pytest.approx(100.0)
    assert (cam.cx, cam.cy) == (W / 2, H / 2)


@pytest.mark.parametrize("lens,dist", [("none", ()), ("division", (-0.04,)),
                                       ("brown", (-0.03, 0.0056))])
def test_ray_and_project_are_inverses(lens, dist):
    cam = make_cam(lens=lens, dist=dist)
    X = np.random.default_rng(1).uniform([0, 0, 0], [11, 24, 3], (30, 3))
    C, d = cam.ray(cam.project(X))
    assert np.allclose(np.linalg.norm(d, axis=1), 1.0)
    s = np.sum((X - C) * d, axis=1)
    assert np.abs(C + s[:, None] * d - X).max() < 1e-6
    g = X.copy()
    g[:, 2] = 0
    assert np.abs(cam.ground_point(cam.project(g)) - g[:, :2]).max() < 1e-6


def test_points_behind_the_camera_are_nan():
    cam = make_cam()
    out = cam.project([[5.0, -20.0, 0.0], [5.0, 10.0, 0.0]])
    assert np.isnan(out[0]).all() and np.isfinite(out[1]).all()


def test_ground_homography_is_the_flat_model():
    from swingvision import calibration
    cam = make_cam()
    corners = [court.LANDMARKS[n] for n in paintfit.CORNERS]
    Hc = calibration.compute_homography(corners, cam.project([(*p, 0.0) for p in corners]))
    G = cam.ground_homography()
    pts = np.random.default_rng(2).uniform([0, 0], [11, 24], (25, 2))
    assert np.abs(calibration.court_to_image(G, pts)
                  - calibration.court_to_image(Hc, pts)).max() < 1e-6


def test_lens_coefficients_are_checked():
    with pytest.raises(ValueError):
        c3.CourtCamera(1000.0, np.zeros(3), [0, 0, 10], (W, H), "division", ())
    with pytest.raises(ValueError):
        c3.CourtCamera(1000.0, np.zeros(3), [0, 0, 10], (W, H), "fisheye", ())


def test_dict_round_trip_is_json_and_exact():
    cam = make_cam(lens="division", dist=(-0.03,))
    cam.extra.update(seed_source="unit", paint_fit=True)
    d = json.loads(json.dumps(cam.to_dict()))
    back = c3.CourtCamera.from_dict(d)
    X = [[1.0, 2.0, 0.5], [9.0, 20.0, 0.0]]
    assert np.allclose(back.project(X), cam.project(X), atol=1e-9)
    assert back.extra == {"seed_source": "unit", "paint_fit": True}
    assert back.pinned_by == "synthetic truth"


# ------------------------------------------------------------- PnP seed -----
@pytest.mark.parametrize("kw", CAMS)
def test_pnp_seed_recovers_an_exact_camera(kw):
    cam = make_cam(**kw)
    kps = visible_keypoints(cam)
    s = c3.solve_pnp_seed(kps, (W, H))
    assert s is not None and not s.dropped_cross_ratio
    assert s.camera.f_px == pytest.approx(cam.f_px, abs=1e-4)
    assert s.camera.position_m() == pytest.approx(cam.position_m(), abs=1e-5)
    assert np.allclose(s.camera.R, cam.R, atol=1e-7)
    assert s.camera.lens == "none" and "PnP" in s.camera.pinned_by


def test_pnp_seed_uses_a_device_focal_as_given():
    cam = make_cam()
    s = c3.solve_pnp_seed(visible_keypoints(cam), (W, H), f_hint=cam.f_px)
    assert s.camera.f_px == cam.f_px
    assert s.camera.position_m() == pytest.approx(cam.position_m(), abs=1e-6)


def test_pnp_seed_rejects_gross_outliers():
    cam = make_cam()
    kps = visible_keypoints(cam)
    bad = ["near_t", "far_sl_left", "net_center_top"]
    for n in bad:
        kps[n] = (kps[n][0] + 160.0, kps[n][1] - 90.0)
    s = c3.solve_pnp_seed(kps, (W, H), use_cross_ratio=False)
    assert s is not None
    assert not set(bad) & set(s.inliers)
    assert s.camera.position_m() == pytest.approx(cam.position_m(), abs=1e-3)


def test_pnp_seed_refuses_too_few_points():
    cam = make_cam()
    kps = dict(list(visible_keypoints(cam).items())[:4])
    assert c3.solve_pnp_seed(kps, (W, H)) is None


def test_pnp_seed_needs_an_image_size():
    with pytest.raises(ValueError):
        c3.solve_pnp_seed({}, None)


def test_pnp_seed_takes_a_keypoint_set():
    cam = make_cam()
    ks = courtfit.KeypointSet(visible_keypoints(cam), source="unit", image_wh=(W, H))
    s = c3.solve_pnp_seed(ks)
    assert s.camera.extra["seed_source"] == "unit"


# ----------------------------------------------------- cross-ratio gate -----
def test_cross_ratio_gate_passes_an_exact_view():
    for kw in CAMS:
        out, report = courtfit.cross_ratio_check(visible_keypoints(make_cam(**kw)), H)
        assert out == set()
        assert report and all(worst < 1e-6 for _, _, worst in report)


def test_cross_ratio_gate_names_a_point_moved_one_metre_along_its_line():
    cam = make_cam()
    kps = visible_keypoints(cam)
    x, y, _ = court.LANDMARKS_3D["near_center_mark"]
    kps["near_center_mark"] = tuple(cam.project([[x + 1.0, y, 0.0]])[0])
    out, _ = courtfit.cross_ratio_check(kps, H)
    assert out == {"near_center_mark"}


def test_cross_ratio_gate_names_a_point_moved_off_its_line():
    cam = make_cam()
    kps = visible_keypoints(cam)
    kps["near_bl_singles"] = (kps["near_bl_singles"][0], kps["near_bl_singles"][1] + 150.0)
    out, _ = courtfit.cross_ratio_check(kps, H)
    assert out == {"near_bl_singles"}


def test_cross_ratio_gate_ignores_detector_grade_noise():
    """CP1's seed noise (sigma 14.78 px at 1080p) is not an outlier: the
    tolerance was set so that noise alone flags a point in well under 1%."""
    cam = make_cam()
    rng = np.random.default_rng(5)
    flagged = 0
    for _ in range(200):
        kps = {n: tuple(np.array(p) + rng.normal(0, 14.78, 2))
               for n, p in visible_keypoints(cam).items()}
        out, _ = courtfit.cross_ratio_check(kps, H)
        flagged += bool(out)
    assert flagged <= 4


def test_cross_ratio_gate_cannot_name_a_culprit_on_a_four_point_line():
    cam = make_cam()
    kps = visible_keypoints(cam)
    x, y, _ = court.LANDMARKS_3D["near_t"]
    kps["near_t"] = tuple(cam.project([[x, y + 1.0, 0.0]])[0])
    out, report = courtfit.cross_ratio_check(kps, H)
    assert out == set()
    assert dict((r[0], r[2]) for r in report)["centre_line"] > 30.0


def test_cross_ratio_gate_scales_with_frame_height():
    cam = make_cam()
    kps = visible_keypoints(cam)
    kps["near_bl_singles"] = (kps["near_bl_singles"][0], kps["near_bl_singles"][1] + 100.0)
    assert courtfit.cross_ratio_check(kps, 720)[0] == {"near_bl_singles"}
    assert courtfit.cross_ratio_check(kps, 2160)[0] == set()


def test_cross_ratio_gate_undistorts_when_the_lens_is_known():
    cam = make_cam(lens="brown", dist=(-0.03, 0.0056))
    kps = visible_keypoints(cam)
    _, report = courtfit.cross_ratio_check(kps, H, undistort=cam.undistort)
    assert all(worst < 1e-6 for _, _, worst in report)
    _, raw = courtfit.cross_ratio_check(kps, H)
    assert max(w for _, _, w in raw) > 1.0      # the lens alone bends the lines


# ------------------------------------------------------------- setup_state --
def test_setup_state_carries_a_camera_without_moving_trust():
    cam = make_cam()
    st = setup_state.with_camera(setup_state.normalize(None), cam)
    assert st["camera"]["f_px"] == pytest.approx(cam.f_px)
    assert st["calibration_status"] == setup_state.CALIB_UNAVAILABLE
    assert st["metrics_eligible"] is False
    back = c3.CourtCamera.from_dict(st["camera"])
    assert np.allclose(back.project([[3, 4, 0]]), cam.project([[3, 4, 0]]))
    json.dumps(st)


def test_setup_state_without_a_camera_is_unchanged():
    assert "camera" not in setup_state.normalize(None)
    assert "camera" not in setup_state.normalize({"framing_status": "clear"})


def test_setup_state_drops_an_unreadable_camera_and_says_so():
    good = make_cam().to_dict()
    for bad in ({"model": "fisheye"}, {**good, "rvec": [0, 0]}, {**good, "f_px": -1},
                {**good, "tvec": [0, float("nan"), 1]}, {**good, "lens": "division"},
                "not a dict"):
        st = setup_state.normalize({"camera": bad})
        assert "camera" not in st
        assert setup_state.CAMERA_UNREADABLE in st["reasons"]
    st = setup_state.normalize({"camera": None})
    assert "camera" not in st and setup_state.CAMERA_UNREADABLE not in st["reasons"]


def test_setup_state_keeps_camera_provenance_keys():
    d = make_cam().to_dict()
    d["seed_source"] = "courtnet:courtnet_split.pt"
    assert setup_state.normalize({"camera": d})["camera"]["seed_source"] == d["seed_source"]
