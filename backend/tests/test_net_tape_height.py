"""Tests for the net-tape camera-height estimator (tools/net_tape_height.py).

Three things are pinned, and each one is a way the estimator could be silently
wrong rather than obviously broken:

  1. THE REPARAMETRISATION. The whole tool rests on the claim that projecting the
     net line at a fake height h' under the FITTED pose lands exactly where the
     real 0.914 m tape would land if the true camera height were
     H = 0.914 * H_fitted / h'. If that identity drifts, the sweep still returns
     a confident number and the number is wrong. Pinned against the closed-form
     horizon relation, independently computed.

  2. RECOVERY. A band planted at a KNOWN height must come back as that height.
     This is the only end-to-end check that the matched filter, the column
     grouping and the h' -> H conversion are wired the right way round: a sign
     error in the conversion still produces plausible metres.

  3. REFUSAL. "I cannot measure this tape" is the answer that makes the estimator
     worth having - its value is that it is independent evidence, and a
     confidently wrong row destroys that. A blank frame must refuse, and two
     equally good bands must refuse as ambiguous rather than pick one.

The camera fixture is `yt_match40`'s shipped corner clicks (1280x720), the
sharpest measurement in the corpus. Nothing here reads or writes a calibration
file; the clicks are inlined so the test cannot be broken by, or break, data/.
"""

import pathlib
import sys

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

_TOOLS = pathlib.Path(__file__).resolve().parents[2] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from swingvision import calibration, court  # noqa: E402

import net_anchor_check as nac  # noqa: E402
import net_tape_height as nth  # noqa: E402

IMG_WH = (1280, 720)
KP = {
    "near_bl_doubles": (107.65169064654117, 454.64901320161266),
    "near_br_doubles": (1357.846948605354, 454.64905748823116),
    "far_br_doubles": (772.2283828889331, 301.14521410308043),
    "far_bl_doubles": (534.621376979253, 300.5401873622284),
}


@pytest.fixture(scope="module")
def cam():
    w, h = IMG_WH
    hfov = nac.hfov_for(KP, w, h)
    assert hfov is not None, "fixture must have a recoverable camera pose"
    h_fit = nth.fitted_height(KP, w, h)
    geo = nac.net_anchor_geometry(KP, IMG_WH, hfov)
    return {"hfov": hfov, "h_fit": h_fit, "geo": geo}


def _project_net(geo, hfov, h_prime, n=120, frac=1.0):
    """The net line projected at height h_prime, as image points."""
    half = frac * (court.X_RIGHT_DOUBLES - court.X_LEFT_DOUBLES) / 2.0
    xs = np.linspace(court.X_CENTER - half, court.X_CENTER + half, n)
    pts = calibration.project_court_3d(
        geo["H"], IMG_WH, [(float(x), court.NET_Y, float(h_prime)) for x in xs], hfov)
    return np.asarray(pts, float)


# ------------------------------------------------------ 1. the reparametrisation

@pytest.mark.parametrize("H_true", [1.20, 1.641, 2.50, 5.00])
def test_fake_height_matches_the_closed_form_horizon_relation(cam, H_true):
    """row(h') under the fitted pose == horizon + (ground-horizon)*(1 - h/H).

    Computed two entirely different ways: the left side goes through the full
    3D projection, the right side is the scalar formula the write-up inverts.
    They must agree to well under the pixel this estimator is sensitive to.
    """
    geo, hfov, h_fit = cam["geo"], cam["hfov"], cam["h_fit"]
    hz, gr = geo["horizon_row"], geo["net_ground_row"]
    h_prime = court.NET_HEIGHT_CENTER * h_fit / H_true
    pts = _project_net(geo, hfov, h_prime)
    row = float(pts[len(pts) // 2][1])
    expected = hz + (gr - hz) * (1.0 - court.NET_HEIGHT_CENTER / H_true)
    assert row == pytest.approx(expected, abs=0.35)


def test_the_tape_images_above_the_net_ground_row(cam):
    """Direction check. A point 0.914 m up must image HIGHER (smaller row) than
    the net's ground line - the ground-vs-tape confusion this project already
    paid for once."""
    geo, hfov = cam["geo"], cam["hfov"]
    pts = _project_net(geo, hfov, court.NET_HEIGHT_CENTER)
    assert float(pts[len(pts) // 2][1]) < geo["net_ground_row"]
    assert geo["net_ground_row"] > geo["horizon_row"]


# ------------------------------------------------------------------ 2. recovery

def _plate_with_band(cam, H_true, bg=40.0, fg=200.0, thick=1, seed=0):
    """A synthetic clean plate carrying one bright band at the row the real tape
    would occupy if the camera were at H_true."""
    rng = np.random.default_rng(seed)
    w, h = IMG_WH
    plate = bg + rng.normal(0.0, 1.0, size=(h, w)).astype(np.float32)
    h_prime = court.NET_HEIGHT_CENTER * cam["h_fit"] / H_true
    pts = _project_net(cam["geo"], cam["hfov"], h_prime, n=600)
    for x, y in pts:
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < w:
            for d in range(-thick, thick + 1):
                if 0 <= yi + d < h:
                    plate[yi + d, xi] = fg
    return cv2.GaussianBlur(plate, (5, 5), 0)


@pytest.mark.parametrize("H_true", [1.40, 1.75, 2.60])
def test_recovers_a_planted_band(cam, H_true):
    plate = _plate_with_band(cam, H_true)
    out = nth.measure_tape_height(plate, KP, IMG_WH, cam["hfov"], cam["h_fit"])
    assert out["refused"] is None, out["refused"]
    # 3% is well inside the 10% bar and well outside a sign error or a
    # h' <-> H inversion, either of which would land somewhere else entirely.
    assert out["tape_H_m"] == pytest.approx(H_true, rel=0.03)


def test_recovery_is_not_just_reporting_the_fitted_height(cam):
    """The planted height is deliberately far from the fitted one. If the tool
    ever collapses to echoing the model, this is what catches it."""
    H_true = 2.60
    out = nth.measure_tape_height(_plate_with_band(cam, H_true), KP, IMG_WH,
                                 cam["hfov"], cam["h_fit"])
    assert abs(out["tape_H_m"] - H_true) < abs(out["tape_H_m"] - cam["h_fit"])


# ------------------------------------------------------------------- 3. refusal

def test_refuses_a_featureless_frame(cam):
    rng = np.random.default_rng(7)
    plate = (40.0 + rng.normal(0.0, 1.0, size=(IMG_WH[1], IMG_WH[0]))).astype(np.float32)
    out = nth.measure_tape_height(cv2.GaussianBlur(plate, (5, 5), 0), KP, IMG_WH,
                                  cam["hfov"], cam["h_fit"])
    assert out["tape_H_m"] is None
    assert out["refused"] is not None


def test_refuses_two_equally_good_bands_as_ambiguous(cam):
    """A fence rail and a tape look the same to a brightness profile. With two
    equal candidates the honest answer is a refusal, not a coin flip.

    Which rule fires is not pinned, only that one does. Measured here: R3 (the
    robust z) fires before R4, because a second strong band inflates the MAD of
    the sweep and flattens the peak's z. That is the same ambiguity caught one
    step earlier, so it is correct; pinning R4 specifically would be pinning an
    implementation detail. R4 does fire in the field - CYqapSq5llo, rival 0.95.
    """
    a = _plate_with_band(cam, 1.45)
    b = _plate_with_band(cam, 2.40)
    plate = np.maximum(a, b)
    out = nth.measure_tape_height(plate, KP, IMG_WH, cam["hfov"], cam["h_fit"])
    assert out["tape_H_m"] is None
    assert out["refused"] is not None
    assert out["refused"][:2] in ("R3", "R4"), out["refused"]


def test_refuses_when_the_camera_pose_is_unrecoverable(cam):
    plate = _plate_with_band(cam, 1.75)
    out = nth.measure_tape_height(plate, KP, IMG_WH, None, cam["h_fit"])
    assert out["tape_H_m"] is None and out["refused"].startswith("R0")
