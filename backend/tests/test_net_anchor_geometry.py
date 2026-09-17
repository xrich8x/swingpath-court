"""Geometry tests for the net-anchor calibration check (tools/net_anchor_check.py).

Two things are pinned here, and both exist because of a live 2026-09-05 mistake:

  1. the net POST constants, so the 0.914 m post offset and the 1.07 m post
     height cannot drift out of court.py unnoticed;
  2. that the projected net TAPE row agrees with the closed-form horizon
     relation, and sits ABOVE the net GROUND row in the image.

(2) is the important one. The `yt_match40` re-click was called wrong because the
projected net GROUND line (court-y 11.885 at z=0, what a homography gives) was
compared against the net's white TOP TAPE in the image, which is 0.914 m higher
and therefore images higher. For a pinhole at height H, (row - horizon) is
proportional to H / depth, so a point h above the ground at the same depth
scales that offset by (H - h) / H. If the tape projection ever stops obeying
that, the tool is drawing the same trap it was built to prevent.
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


# ------------------------------------------------------------------ constants

def test_net_post_constants():
    assert court.NET_POST_OFFSET == pytest.approx(0.914)
    assert court.NET_HEIGHT_POST == pytest.approx(1.07)
    assert court.NET_HEIGHT_CENTER == pytest.approx(0.914)
    # Doubles posts stand OUTSIDE the doubles sidelines.
    assert court.X_LEFT_POST == pytest.approx(-0.914)
    assert court.X_RIGHT_POST == pytest.approx(11.884)
    assert court.X_LEFT_POST < court.X_LEFT_DOUBLES
    assert court.X_RIGHT_POST > court.X_RIGHT_DOUBLES
    # Singles sticks stand INSIDE the doubles alley - different geometry, and
    # code that cares which it is looking at must choose deliberately.
    assert court.X_LEFT_STICK == pytest.approx(0.456)
    assert court.X_RIGHT_STICK == pytest.approx(10.514)
    assert court.X_LEFT_DOUBLES < court.X_LEFT_STICK < court.X_LEFT_SINGLES
    assert court.X_RIGHT_SINGLES < court.X_RIGHT_STICK < court.X_RIGHT_DOUBLES


def test_net_posts_are_not_fitted_points():
    """The whole non-circularity claim: no net anchor is one of the four corners
    a manual calibration is fitted to, nor any named landmark."""
    fitted = set(nac.CORNERS)
    assert fitted <= set(court.LANDMARKS)
    for name, xy in court.NET_POST_BASES.items():
        assert name not in court.LANDMARKS
        assert xy not in [court.LANDMARKS[n] for n in fitted]
    assert (court.X_CENTER, court.NET_Y) not in [court.LANDMARKS[n] for n in fitted]


def test_post_segments_are_vertical_and_full_height():
    for name, (base, top) in court.net_post_segments_3d().items():
        assert base[:2] == top[:2], f"{name} is not vertical"
        assert base[2] == 0.0
        assert top[2] == pytest.approx(court.NET_HEIGHT_POST)


def test_net_height_at_runs_centre_strap_to_post():
    assert nac.net_height_at(court.X_CENTER) == pytest.approx(court.NET_HEIGHT_CENTER)
    assert nac.net_height_at(court.X_LEFT_POST) == pytest.approx(court.NET_HEIGHT_POST)
    assert nac.net_height_at(court.X_RIGHT_POST) == pytest.approx(court.NET_HEIGHT_POST)
    mid = nac.net_height_at(court.X_LEFT_DOUBLES)
    assert court.NET_HEIGHT_CENTER < mid < court.NET_HEIGHT_POST


# ------------------------------------------------------------------- geometry

W, H_PX, HFOV, CAM_H = 1280, 720, 68.0, 1.64


def _synthetic_corners():
    """Image positions of the four doubles corners under a known camera:
    CAM_H metres up, behind the near baseline, looking at the court centre.
    A round trip through this is what makes the tape assertion meaningful."""
    eye = np.array([court.X_CENTER, -4.0, CAM_H])
    tgt = np.array([court.X_CENTER, court.NET_Y, 0.0])
    fwd = tgt - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0.0, 0.0, 1.0]))
    right /= np.linalg.norm(right)
    down = np.cross(fwd, right)
    R = np.vstack([right, down, fwd])                 # world -> camera
    tvec = -R @ eye
    fx = (W / 2.0) / np.tan(np.radians(HFOV) / 2.0)
    K = np.array([[fx, 0, W / 2.0], [0, fx, H_PX / 2.0], [0, 0, 1.0]])
    world = np.array([[*court.LANDMARKS[n], 0.0] for n in nac.CORNERS], float)
    px, _ = cv2.projectPoints(world, cv2.Rodrigues(R)[0], tvec, K, None)
    return {n: tuple(p) for n, p in zip(nac.CORNERS, px.reshape(-1, 2))}


def test_tape_row_matches_the_closed_form_horizon_relation():
    kp = _synthetic_corners()
    geo = nac.net_anchor_geometry(kp, (W, H_PX), HFOV)
    hz, gnd, tape = geo["horizon_row"], geo["net_ground_row"], geo["net_tape_row"]
    assert hz is not None and tape is not None

    # The tape is ABOVE the ground line in the image. Reading one against the
    # other is the apples-to-oranges error; this is the guard against it.
    assert tape < gnd, "net tape must image ABOVE the net ground line"

    # (row - horizon) scales by (H - h) / H at fixed depth.
    expect = hz + (gnd - hz) * (CAM_H - court.NET_HEIGHT_CENTER) / CAM_H
    assert tape == pytest.approx(expect, abs=1.0), (
        f"tape row {tape} but the horizon relation says {expect:.1f} "
        f"(horizon {hz}, ground {gnd}, camera {CAM_H} m)")

    # ... and the gap is a real, visible number, not a rounding artefact.
    assert (gnd - tape) > 5.0


def test_homography_round_trips_the_fitted_corners():
    """A calibration check that cannot reproduce its own inputs is measuring the
    solver, not the clicks."""
    kp = _synthetic_corners()
    geo = nac.net_anchor_geometry(kp, (W, H_PX), HFOV)
    back = calibration.court_to_image(geo["H"], [court.LANDMARKS[n] for n in nac.CORNERS])
    for n, p in zip(nac.CORNERS, back):
        assert p[0] == pytest.approx(kp[n][0], abs=0.5)
        assert p[1] == pytest.approx(kp[n][1], abs=0.5)


def test_posts_straddle_the_court_in_the_image():
    """Left post left of the left doubles sideline at the net, right post right
    of the right one - the ordering that makes a post a usable visual anchor."""
    kp = _synthetic_corners()
    geo = nac.net_anchor_geometry(kp, (W, H_PX), HFOV)
    left_edge, right_edge = geo["net_ground"][0], geo["net_ground"][-1]
    assert geo["post_bases"]["net_post_left"][0] < left_edge[0]
    assert geo["post_bases"]["net_post_right"][0] > right_edge[0]
    for name, top in geo["post_tops"].items():
        assert top is not None
        assert top[1] < geo["post_bases"][name][1], f"{name} top is not above its base"
