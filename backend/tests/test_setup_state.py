"""The persisted trust state: what a camera setup may claim, and what it may not.

Synthetic cameras only — no footage, no weights — so every case here is exactly
reproducible. `_cam` is the same pinhole construction test_setup_guide.py uses:
a centre-line camera `back` metres behind the baseline at height `Cz`. Camera
HEIGHT is what the clearance margin actually tracks (Spearman +0.937 over 28 real
calibrations; the far/near width ratio manages +0.189), so heights are the right
knob for producing clear / limited / overlap fixtures.

THE THREE FIXTURE HEIGHTS are read off the shipped bands, not invented here:
the geometric crossover is 1.98-2.21 m and the +10 px comfortable band starts at
2.28-2.98 m (docs/evidence/live-setup-criterion.md). So ~1.5 m is overlap, ~3.4 m
is clear, and the sliver between them is limited. The test asserts the BAND each
one lands in via the shipped criterion — it never re-derives the criterion.

WHAT THIS FILE IS NOT ALLOWED TO BECOME: a gate test. Every assertion here is
about what the product SAYS. If a future change makes any of this refuse a clip,
`test_nothing_here_ever_refuses_a_recording` should fail, and if somebody deletes
that test the whole design is gone with it.
"""

import math

import numpy as np
import pytest

from swingvision import court
from swingvision import setup_state as ss

pytest.importorskip("scipy")

from swingvision import calibration as C  # noqa: E402

DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]
W, H = 1280, 720


def _cam(Cz, hfov_deg=74.0, back=8.0):
    """Homography for a centre-line camera `back` m behind the baseline at Cz."""
    f_px = W / (2.0 * math.tan(math.radians(hfov_deg) / 2.0))
    Cx, Cy = court.DOUBLES_WIDTH / 2.0, -back
    pitch = math.atan2(Cz, back + court.LENGTH * 0.5)
    st, ct = math.sin(pitch), math.cos(pitch)
    fwd = np.array([0.0, ct, -st])
    right = np.array([1.0, 0.0, 0.0])
    up = np.array([0.0, st, ct])
    img, wld = [], []
    for n in DBL:
        X, Y = court.LANDMARKS[n]
        d = np.array([X - Cx, Y - Cy, -Cz])
        z = d @ fwd
        img.append([W / 2 + f_px * (d @ right) / z, H / 2 - f_px * (d @ up) / z])
        wld.append([X, Y])
    return C.compute_homography(wld, img)


#: One mount per band. Named so a failure says which product state broke.
CLEAR_MOUNT_M = 3.4
OVERLAP_MOUNT_M = 1.5


def _state(Cz, **kw):
    return ss.from_homography(_cam(Cz), (W, H), **kw)


def _limited_state(**kw):
    """A `limited` state, found by walking the band the criterion itself defines
    rather than by hard-coding a height. The marginal band is narrow (0 to +10 px
    at 720p, roughly 2.0-2.9 m), so a fixed number here would be a re-derivation
    of the criterion and would rot the moment the geometry is refined."""
    for cz in np.arange(2.0, 3.0, 0.02):
        st = _state(float(cz), **kw)
        if st.framing_status == ss.FRAMING_LIMITED:
            return st, float(cz)
    pytest.fail("no camera height in 2.0-3.0 m produced a `limited` framing state")


# --- the three framing states -----------------------------------------------
def test_a_high_mount_is_clear():
    st = _state(CLEAR_MOUNT_M)
    assert st.framing_status == ss.FRAMING_CLEAR
    assert st.far_baseline_clearance_px_720 > 0
    assert st.notice is None, "a clear setup must not show a limitation notice"


def test_a_phone_height_mount_is_overlap():
    """1.5 m is a standing tripod, and it is the normal amateur case: 16 of the
    28 real calibrations in this repo are below the crossover."""
    st = _state(OVERLAP_MOUNT_M)
    assert st.framing_status == ss.FRAMING_OVERLAP
    assert st.far_baseline_clearance_px_720 <= 0
    assert st.notice["title"] == ss.OVERLAP_TITLE


def test_the_band_between_is_limited():
    st, cz = _limited_state()
    assert st.framing_status == ss.FRAMING_LIMITED
    assert 0 < st.far_baseline_clearance_px_720 < C.CLEARANCE_GOOD_PX
    assert st.notice["title"] == ss.LOW_CAMERA_TITLE
    assert 1.9 < cz < 3.0, f"limited band landed at {cz} m, outside the derived range"


def test_the_states_are_ordered_by_mount_height():
    """The whole product claim in one assertion: raising the phone improves the
    state, and nothing else in this module can reorder them."""
    order = {ss.FRAMING_OVERLAP: 0, ss.FRAMING_LIMITED: 1, ss.FRAMING_CLEAR: 2}
    seq = [order[_state(cz).framing_status] for cz in (1.4, 1.8, 3.0, 4.0)]
    assert seq == sorted(seq), seq


# --- the second axis: who placed the corners --------------------------------
def test_clear_framing_alone_does_not_make_metrics_verified():
    """Trap T23: `yt_match40` passed a 0.9 px residual with all four corners on
    asphalt. Good framing says the information is IN the image; it says nothing
    about whether the court was put in the right place."""
    st = _state(CLEAR_MOUNT_M, calibration_status=ss.CALIB_PROVISIONAL)
    assert st.framing_status == ss.FRAMING_CLEAR
    assert st.metrics_eligible is False
    assert any("provisional" in r for r in st.reasons)


def test_confirmation_alone_does_not_make_metrics_verified():
    """Confirming corners cannot put information into an image that never had
    it. A hand-confirmed 1.5 m mount is still `overlap`."""
    st = _state(OVERLAP_MOUNT_M, calibration_status=ss.CALIB_USER_CONFIRMED)
    assert st.metrics_eligible is False


def test_both_axes_good_is_the_only_verified_state():
    st = _state(CLEAR_MOUNT_M, calibration_status=ss.CALIB_USER_CONFIRMED)
    assert st.metrics_eligible is True
    assert st.notice is None


def test_exact_flag_never_counts_as_a_human_confirmation():
    """TRAP T26, pinned. `_exact` meant 'the Shape lock checkbox was off' and was
    read downstream as 'a human deliberately placed these'. It never established
    who placed anything, and the founder later marked 10 of 28 such placements
    wrong. It must not be a route to `user_confirmed`."""
    status, _ = ss.calibration_status_from_keypoints({"_exact": True}, "manual-exact")
    assert status == ss.CALIB_PROVISIONAL


def test_unattributed_provenance_is_not_a_human_confirmation():
    """The setup tool's honest default. It serves a localhost page and cannot
    tell a person's mouse from an agent's HTTP POST, so it says so."""
    raw = {"_provenance": {"placed_by": "unattributed", "shape_lock": False}}
    status, reasons = ss.calibration_status_from_keypoints(raw, "manual")
    assert status == ss.CALIB_PROVISIONAL
    assert reasons and "provisional" in reasons[0]


def test_an_explicit_confirmation_is_what_counts():
    raw = {"_provenance": {"placed_by": "unattributed",
                           "confirmed_by_user": True,
                           "confirmed_corners": DBL}}
    status, _ = ss.calibration_status_from_keypoints(raw, "manual")
    assert status == ss.CALIB_USER_CONFIRMED


def test_an_auto_detected_court_is_provisional_and_says_so():
    status, reasons = ss.calibration_status_from_keypoints(None, "auto-court(7/8)")
    assert status == ss.CALIB_PROVISIONAL
    assert "auto-court(7/8)" in reasons[0]


# --- the user's own answer (Feature 1, before any calibration exists) --------
def test_the_user_answer_alone_can_produce_a_state():
    """The question is asked in a live preview, where no homography exists. The
    answer is the ONLY signal at that moment, and it must produce something."""
    st = ss.build(far_baseline_user_answer=False)
    assert st.framing_status == ss.FRAMING_OVERLAP
    assert st.framing_source == "user_answer"
    assert st.far_baseline_clearance_px_720 is None
    assert st.metrics_eligible is False, "no calibration exists yet"


def test_unsure_is_a_real_answer_and_stays_unknown():
    st = ss.build(far_baseline_user_answer=None)
    assert st.framing_status == ss.FRAMING_UNKNOWN


def test_a_human_answer_can_never_produce_limited():
    """Nobody can judge '+7 px at 720p' by eye. `limited` is reserved for the
    measured margin, so an answer maps only to clear / overlap / unknown."""
    for answer in (True, False, None):
        assert ss.framing_from_user_answer(answer) != ss.FRAMING_LIMITED


def test_geometry_overrides_the_answer_and_records_the_disagreement():
    """The user glanced at a preview; the margin is measured from the corners
    they themselves placed. Geometry wins - but silently picking a winner is how
    a user learns their app ignores them, so the disagreement is written down."""
    st = _state(OVERLAP_MOUNT_M, far_baseline_user_answer=True)
    assert st.framing_status == ss.FRAMING_OVERLAP
    assert st.framing_source == "clearance_geometry"
    assert st.far_baseline_user_answer is True, "the answer must be kept, not erased"
    assert any("disagree" in r for r in st.reasons)


def test_agreement_produces_no_disagreement_reason():
    st = _state(CLEAR_MOUNT_M, far_baseline_user_answer=True)
    assert not any("disagree" in r for r in st.reasons)


# --- degradation ------------------------------------------------------------
def test_a_quad_no_camera_fits_degrades_to_unknown_not_to_clear():
    """`net_tape_clearance` returns None when no physical camera fits the quad.
    The failure direction matters: not-measurable must never render as verified."""
    bad = C.compute_homography(
        [court.LANDMARKS[n] for n in DBL],
        [[100, 400], [540, 400], [700, 200], [50, 205]])
    st = ss.from_homography(bad, (W, H),
                            calibration_status=ss.CALIB_USER_CONFIRMED)
    if st.far_baseline_clearance_px_720 is None:
        assert st.framing_status == ss.FRAMING_UNKNOWN
        assert st.metrics_eligible is False


def test_every_state_carries_at_least_one_plain_english_reason():
    """A user told 'limited' with no explanation has been given a mood, not
    information."""
    for cz in (1.4, 2.4, 3.4):
        for status in ss.CALIBRATION_STATUSES:
            st = _state(cz, calibration_status=status)
            assert st.reasons, f"{cz} m / {status} produced no reasons"
            assert all(isinstance(r, str) and r.strip() for r in st.reasons)


# --- backwards compatibility -------------------------------------------------
def test_a_missing_block_normalizes_to_unknown():
    n = ss.normalize(None)
    assert n["framing_status"] == ss.FRAMING_UNKNOWN
    assert n["calibration_status"] == ss.CALIB_UNAVAILABLE
    assert n["metrics_eligible"] is False
    assert n["reasons"], "unknown must still explain itself"


@pytest.mark.parametrize("raw", [
    None, {}, [], "clear", 7,
    {"framing_status": "excellent"},                       # unknown vocabulary
    {"framing_status": None, "calibration_status": None},
    {"framing_status": "clear", "far_baseline_clearance_px_720": "lots"},
    {"reasons": "not a list"},
])
def test_normalize_never_raises_and_never_invents_verified(raw):
    n = ss.normalize(raw)
    assert n["framing_status"] in ss.FRAMING_STATUSES
    assert n["calibration_status"] in ss.CALIBRATION_STATUSES
    assert n["metrics_eligible"] is False


def test_normalize_refuses_a_hand_edited_verified_claim():
    """`metrics_eligible` is RE-DERIVED, never trusted from the file. Otherwise
    editing one boolean in a JSON promotes an unverifiable match to verified."""
    n = ss.normalize({"framing_status": "overlap",
                      "calibration_status": "provisional",
                      "metrics_eligible": True})
    assert n["metrics_eligible"] is False


def test_normalize_is_idempotent():
    once = ss.normalize(_state(CLEAR_MOUNT_M).to_dict())
    assert ss.normalize(once) == once


# --- the design constraint ---------------------------------------------------
def test_nothing_here_ever_refuses_a_recording():
    """THE LOAD-BEARING TEST. Five autonomous accept/reject gates have failed on
    this project; the clearance criterion was built as the thing that is not a
    sixth, and this module inherits that. There is no boolean anywhere in a
    SetupState that means 'refuse', and `metrics_eligible` is a statement about
    PRESENTATION. If a future change makes this a gate, delete the design or
    delete this test - do not quietly do both."""
    for cz in (1.0, 1.5, 2.4, 3.4, 8.0):
        st = _state(cz)
        d = st.to_dict()
        assert set(d) == {
            "framing_status", "far_baseline_clearance_px_720",
            "calibration_status", "metrics_eligible", "reasons",
            "framing_source", "far_baseline_user_answer", "notice"}
        for key in ("blocked", "refused", "allowed", "can_record", "reject"):
            assert key not in d


def test_both_notices_offer_continue_first():
    for status in (ss.FRAMING_LIMITED, ss.FRAMING_OVERLAP):
        assert ss.notice_for(status)["actions"][0] == "Continue with this setup"
