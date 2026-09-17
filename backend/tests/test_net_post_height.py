"""Pins tools/net_post_height.py - the NET-POST camera-height estimator.

The detector FAILED its pre-registered bar (3 of 11 confident clips within 10% of
the fitted height, against a 2/3 bar; docs/evidence/net-post-detector.md). These
tests exist anyway, and specifically pin the things a later "improvement" would be
tempted to quietly change:

  * the reparametrisation H = 1.07 * H_fitted / h', which is the whole estimator;
  * the sign-agnosticism of the `postness` response (a post is dark against sky
    AND light against a dark fence - a filter that only finds one is a different
    instrument);
  * every refusal constant, at the value it had when the bar was run. A failed bar
    stays failed, and a constant edited later silently un-fails it;
  * that the post's per-pixel sensitivity is 0.914/1.07 = 0.854x the tape's - the
    one measured advantage the post has, and the one a reader is most likely to
    mis-state in the other direction.
"""

import pathlib
import sys

import numpy as np
import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
for p in (REPO / "backend", REPO / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from swingvision import court as _court            # noqa: E402

nph = pytest.importorskip("net_post_height")


# ---- the reparametrisation ---------------------------------------------------

def test_h_prime_inverts_to_camera_height():
    """h' = the post height that WOULD land where the real 1.07 m post lands if
    the camera were at H. So h' = 1.07 exactly when H == H_fitted."""
    h_fit = 1.641
    for hp, want in [(_court.NET_HEIGHT_POST, h_fit),
                     (_court.NET_HEIGHT_POST / 2.0, 2 * h_fit),
                     (_court.NET_HEIGHT_POST * 2.0, h_fit / 2.0)]:
        assert _court.NET_HEIGHT_POST * h_fit / hp == pytest.approx(want, rel=1e-9)


def test_pinhole_row_law_round_trips():
    """row = horizon + (ground-horizon)*(1 - h/H) must invert to the same H."""
    hz, gr, H, h = 264.8, 325.4, 1.641, _court.NET_HEIGHT_POST
    row = hz + (gr - hz) * (1.0 - h / H)
    t = (row - hz) / (gr - hz)
    assert h / (1.0 - t) == pytest.approx(H, rel=1e-9)


# ---- the instrument's price --------------------------------------------------

def test_post_is_more_sensitive_per_pixel_than_the_tape():
    """dH/drow = H^2/(h*(ground-horizon)). The post's h is LARGER, so its %/px is
    SMALLER - the post is 0.854x the tape per pixel of row error. This is the
    post's only measured advantage; it does not survive its row precision."""
    hz, gr, H = 264.8, 325.4, 1.641
    post = 100.0 * H / (_court.NET_HEIGHT_POST * abs(gr - hz))
    tape = 100.0 * H / (_court.NET_HEIGHT_CENTER * abs(gr - hz))
    assert post < tape
    assert post / tape == pytest.approx(_court.NET_HEIGHT_CENTER
                                        / _court.NET_HEIGHT_POST, rel=1e-9)
    assert post / tape == pytest.approx(0.854, abs=0.002)


# ---- the response ------------------------------------------------------------

def _bar_plate(bright, w=200, h=200, col=100, half=2, top=60):
    """A synthetic vertical bar from row `top` down, `2*half+1` px wide."""
    bg, fg = (40.0, 200.0) if bright else (200.0, 40.0)
    img = np.full((h, w), bg, np.float32)
    img[top:, col - half:col + half + 1] = fg
    return img


def _column_pts(col=100, rows=None):
    rows = np.arange(200.0, 0.0, -1.0) if rows is None else rows
    return np.stack([np.full_like(rows, float(col)), rows], axis=1)


@pytest.mark.parametrize("bright", [True, False])
def test_postness_is_sign_agnostic(bright):
    """A dark post on sky must score as strongly as a light post on a dark fence.
    max(min(on-l,on-r), min(l-on,r-on)) is what buys that."""
    plate = _bar_plate(bright)
    pn = nph._perp_samples(plate, _column_pts(), 1.0)
    on_bar = pn[:130]          # sampled downward-to-upward; rows 200..70 are bar
    assert np.nanmedian(on_bar) > 100.0


def test_postness_is_near_zero_off_the_bar():
    plate = _bar_plate(True)
    pn = nph._perp_samples(plate, _column_pts(col=40), 1.0)
    assert abs(float(np.nanmedian(pn))) < 1.0


def test_step_response_peaks_at_the_top_of_the_bar():
    """The measurand is a STEP in postness, not a peak in it."""
    plate = _bar_plate(True, top=60)
    rows = np.arange(199.0, 0.0, -0.5)          # increasing height = decreasing row
    pn = nph._perp_samples(plate, _column_pts(rows=rows), 1.0)
    resp = nph._step_response(pn, 8)
    j = int(np.nanargmax(resp))
    assert rows[j] == pytest.approx(60.0, abs=3.0)


def test_step_response_is_nan_within_a_window_of_each_end():
    resp = nph._step_response(np.ones(50), 8)
    assert np.isnan(resp[:8]).all() and np.isnan(resp[-8:]).all()
    assert np.isfinite(resp[8:-8]).all()


# ---- the refusal constants, pinned at the values the bar was run with --------

def test_refusal_constants_are_the_tapes():
    """P2-P5 reuse net_tape_height's constants so the two instruments are judged
    equally strictly. If these drift, the post's 3/11 is no longer comparable to
    the tape's 13/15 and the verdict in the evidence doc becomes unreadable."""
    import net_tape_height as nth
    assert nph.MIN_EDGE == nth.MIN_SCORE == 4.0
    assert nph.MIN_Z == nth.MIN_Z == 4.0
    assert (nph.RIVAL_SEP_PX, nph.RIVAL_FRAC) == (nth.RIVAL_SEP_PX, nth.RIVAL_FRAC)
    assert nph.MAX_SPREAD_PX == nth.MAX_SPREAD_PX == 3.0
    assert (nph.H_MIN, nph.H_MAX) == (nth.H_MIN, nth.H_MAX)


def test_p6_is_absolute_not_resolution_scaled():
    """An edge on a 6 px bar is unmeasurable at ANY sensor resolution, so the
    resolvability floor is absolute pixels - the one place the project's
    frame_height/720 rule deliberately does not apply."""
    assert nph.MIN_POST_PX == 10.0
    src = pathlib.Path(nph.__file__).read_text(encoding="utf-8")
    line = [ln for ln in src.splitlines() if ln.startswith("MIN_POST_PX")][0]
    assert "ABSOLUTE" in line


def test_p6_refuses_a_post_too_short_to_measure():
    geo = {"post_bases": {"net_post_left": (100.0, 200.0)},
           "post_tops": {"net_post_left": (100.0, 194.0)},      # 6 px
           "H": None}
    out = nph.measure_post(np.zeros((300, 300), np.float32), geo, "net_post_left",
                           (300, 300), 90.0, 1.6, 40.0, 1.0)
    assert out["post_H_m"] is None and out["refused"].startswith("P6")
    assert out["post_px"] == 6.0


def test_unprojectable_post_top_refuses_p0():
    geo = {"post_bases": {"net_post_left": (100.0, 200.0)},
           "post_tops": {"net_post_left": None}, "H": None}
    out = nph.measure_post(np.zeros((300, 300), np.float32), geo, "net_post_left",
                           (300, 300), 90.0, 1.6, 40.0, 1.0)
    assert out["post_H_m"] is None and out["refused"].startswith("P0")


# ---- the diagnostics must never feed a decision ------------------------------

def test_diagnostics_are_never_read_by_a_rule():
    """diag_* fields compare against the FITTED height. If any refusal rule ever
    read one, the estimator would be grading its own homework (hard rule 1)."""
    src = pathlib.Path(nph.__file__).read_text(encoding="utf-8")
    body = src.split("def _diagnose", 1)[1].split("\ndef ", 1)[1]
    assert "diag_" not in body, "a diag_ field is being consumed downstream"


def test_no_gate_language_in_the_tool():
    """This is a diagnostic number for a human. Four autonomous gates have failed
    in this family; this is not a fifth."""
    src = pathlib.Path(nph.__file__).read_text(encoding="utf-8").upper()
    assert "NOT A GATE" in src
