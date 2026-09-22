"""G8: the far-line instrument, and what a lock now CLAIMS.

`camera3d.paint_check` used to drop `far_baseline` and `far_service` before any
threshold applied - their 5 cm of paint runs in depth and projects under a pixel -
so it answered yes/no while blind to the two lines every court failure lands on
(qa audit 2026-09-18 s7). These tests pin the mechanism and the semantics, NOT the
measured catch rate: that lives in docs/evidence/court-camera3d.md, G8.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
S = pytest.importorskip("court_track_sim")

from swingvision import camera3d, setup_state  # noqa: E402

WH = (1920, 1080)


@pytest.fixture(scope="module")
def scene():
    """One 1080p frame from a known camera, rendered in the only mode that can
    place sub-pixel paint at all (jittered sub-samples, PSF before binning)."""
    p0 = S.base_pitch(WH)
    cam = S.camera(0.0, p0, 0.0, wh=WH)
    img = np.clip(S.render(cam, np.random.default_rng(700), subpixel=True),
                  0, 255).astype(np.uint8)
    return cam, img, p0


# ------------------------------------------------------- the segment rule --
def _profile(offset, amp=10.0, sd=0.3, n=61, reach=7.5, seed=0):
    s = np.linspace(-reach, reach, n)
    rng = np.random.default_rng(seed)
    return s, 100.0 + amp * np.exp(-0.5 * ((s - offset) / 1.0) ** 2) + rng.normal(0, sd, n)


def test_a_ridge_on_the_prediction_is_a_hit():
    s, P = _profile(0.0)
    det, hit, z, off = camera3d._seg_hit(s, P, 0.3, 5.0)
    assert det and hit and z > 5 and abs(off) < 0.3


def test_a_ridge_off_the_prediction_is_seen_but_not_a_hit():
    s, P = _profile(2.0)
    det, hit, z, off = camera3d._seg_hit(s, P, 0.3, 5.0)
    assert det and not hit and abs(off - 2.0) < 0.3


def test_no_ridge_at_all_is_NOT_reported_as_a_failed_line():
    """The load-bearing distinction: a profile with no ridge anywhere cannot tell
    a wrong camera from paint too faint to see, so it is UNCHECKABLE, not failed."""
    s, P = _profile(0.0, amp=0.0)
    det, hit, _z, _off = camera3d._seg_hit(s, P, 0.3, 5.0)
    assert not det and not hit


# --------------------------------------------------- the far lines are SEEN --
def test_the_instrument_is_SHIPPED_OFF_and_says_so(scene):
    """G8's non-degradation bar FAILED on CP1's cluttered scene (369 of 369 right
    cameras flagged; the net tape captures the ridge), so the instrument ships
    measured but OFF. Re-decided 2026-09-22 at the REGISTERED window (3 x
    far_tol): bar 3 fails there instead (a 49 cm knock frame locks as whole_court)
    and bar 4 passes only because the far lines go unchecked. A failed gate stays
    failed - do not flip this default without a new pre-registration."""
    cam, img, _ = scene
    assert camera3d.FAR_LINES_DEFAULT is False
    d = camera3d.paint_check(img, cam)
    assert set(camera3d.FAR_LINES) <= set(d.unchecked)
    assert d.scope == "near_half" and not d.far_lines_checked
    assert "far_baseline" in d.claim()


def test_the_far_lines_move_from_unchecked_to_checked(scene):
    cam, img, _ = scene
    before = camera3d.paint_check(img, cam, far_lines=False)
    after = camera3d.paint_check(img, cam, far_lines=True)
    assert set(camera3d.FAR_LINES) <= set(before.unchecked)      # the pre-G8 blind spot
    assert set(camera3d.FAR_LINES) <= set(after.lines)
    assert after.ok and after.scope == "whole_court" and after.far_lines_checked


def test_the_far_path_changes_nothing_on_the_lines_that_were_already_wide(scene):
    """Rule 7 in a test: the far path runs only on samples the width filter
    DROPPED, so every previously-checked fraction must be bit-identical."""
    cam, img, _ = scene
    before = camera3d.paint_check(img, cam, far_lines=False)
    after = camera3d.paint_check(img, cam, far_lines=True)
    for name, (frac, n) in before.lines.items():
        wide = after.detail[name]["wide"]
        assert wide == (frac, n), name


def test_a_far_line_off_by_metres_is_caught(scene):
    cam, img, p0 = scene
    bad = S.camera(0.0, p0 + math.radians(0.25), 0.0, wh=WH)
    assert camera3d.paint_check(img, bad, far_lines=True).ok is False


def test_the_instrument_reads_no_far_line_position_from_the_model(scene):
    """It samples at offsets FROM the camera's own prediction: shift the camera
    and the reported offsets must shift with it, not stay put."""
    cam, img, p0 = scene
    a = camera3d.far_line_profile(img, cam)["far_baseline"]
    bad = S.camera(0.0, p0 + math.radians(0.05), 0.0, wh=WH)
    b = camera3d.far_line_profile(img, bad)["far_baseline"]
    oa = [o for o in a["off"] if o is not None]
    ob = [o for o in b["off"] if o is not None]
    assert oa and ob and abs(np.mean(ob) - np.mean(oa)) > 0.2


def test_the_sweep_scores_the_same_measurements_it_stacked(scene):
    """far_line_profile must equal stacks -> score_far_stacks, or the G8 sweep
    scored something the shipped check does not compute."""
    cam, img, _ = scene
    direct = camera3d.far_line_profile(img, cam, far_tol_px_720=0.3, far_min_z=4.0)
    # the registered window follows the tolerance (G8: reach = 3 x far_tol), so a
    # re-score of stacked profiles is only the same measurement at the same reach
    st = camera3d.far_line_stacks(img, cam, reach_px_720=camera3d.FAR_REACH_MULT * 0.3)
    via = camera3d.score_far_stacks(st, far_tol_px_720=0.3, far_min_z=4.0,
                                    s_scale=WH[1] / 720.0)
    assert direct == via


# ------------------------------------------------------- honest semantics --
def test_paint_check_says_what_it_verified(scene):
    cam, img, _ = scene
    whole = camera3d.paint_check(img, cam, far_lines=True)
    near = camera3d.paint_check(img, cam, far_lines=False)
    assert whole.claim() == "whole court verified against the paint"
    assert near.scope == "near_half" and "far_baseline" in near.claim()
    assert not near.far_lines_checked


def test_a_track_step_says_what_it_verified(scene):
    from swingvision import camtrack
    cam, img, _ = scene
    tr = camtrack.CameraTracker(cam, paint_fit=lambda *a, **k: None,
                                cfg=camtrack.TrackConfig(far_lines=True))
    st = tr.step(img, 0.0)
    assert st.lock_scope in ("whole_court", "near_half", "none")
    assert st.claim().startswith("locked") or st.claim().startswith("not locked")
    if st.lock_scope == "near_half":
        assert "NOT verified" in st.claim()


def test_a_camera_with_no_recorded_scope_reads_as_unknown_never_whole_court():
    cam = camera3d.CourtCamera(800.0, [1.8, 0, 0], [-5, 1, 6], WH)
    d = setup_state.normalize_camera(cam.to_dict())
    assert d["lock_scope"] == setup_state.LOCK_UNKNOWN
    assert "not recorded" in d["lock_claim"]


def test_a_hand_written_claim_cannot_out_claim_its_scope():
    cam = camera3d.CourtCamera(800.0, [1.8, 0, 0], [-5, 1, 6], WH)
    raw = cam.to_dict()
    raw["lock_scope"] = "near_half"
    raw["lock_unverified"] = ["far_baseline"]
    raw["lock_claim"] = "Every court line was checked against the paint."
    d = setup_state.normalize_camera(raw)
    assert d["lock_claim"] != raw["lock_claim"]
    assert "NOT checked: far_baseline" in d["lock_claim"]


def test_an_unknown_scope_string_is_refused():
    cam = camera3d.CourtCamera(800.0, [1.8, 0, 0], [-5, 1, 6], WH)
    raw = cam.to_dict()
    raw["lock_scope"] = "totally_verified_trust_me"
    assert setup_state.normalize_camera(raw)["lock_scope"] == setup_state.LOCK_UNKNOWN


# ------------------------------------------ the scope is cross-checked too --
# qa 2026-09-19, claim 8: the CLAIM could never exceed the scope, but the SCOPE
# was free text and nothing compared it with `lock_unverified` beside it.
def _forged(scope, unver):
    cam = camera3d.CourtCamera(800.0, [1.8, 0, 0], [-5, 1, 6], WH)
    raw = cam.to_dict()
    raw["lock_scope"] = scope
    raw["lock_unverified"] = unver
    raw["lock_claim"] = "Every court line was checked against the paint."
    return setup_state.normalize_camera(raw)


def test_whole_court_beside_unverified_lines_is_REFUSED_qa_attack_verbatim():
    d = _forged("whole_court", ["far_baseline", "far_service"])
    assert d["lock_scope"] == setup_state.LOCK_UNKNOWN
    assert d["lock_scope_refused"] == "whole_court"
    assert "Every court line" not in d["lock_claim"]
    assert "NOT checked: far_baseline, far_service" in d["lock_claim"]


def test_whole_court_beside_a_BARE_STRING_unverified_is_refused_too():
    for unver in ("far_baseline", {"far_baseline": 1}, 7):
        d = _forged("whole_court", unver)
        assert d["lock_scope"] == setup_state.LOCK_UNKNOWN, unver
        assert "Every court line" not in d["lock_claim"], unver


def test_the_refusal_survives_a_second_read():
    d = setup_state.normalize_camera(_forged("whole_court", ["far_baseline"]))
    assert d["lock_scope"] == setup_state.LOCK_UNKNOWN
    assert "Every court line" not in d["lock_claim"]


def test_a_CONSISTENT_whole_court_block_still_says_so():
    for unver in ([], None, ""):
        d = _forged("whole_court", unver)
        assert d["lock_scope"] == "whole_court", unver
        assert "lock_scope_refused" not in d
        assert d["lock_claim"] == "Every court line was checked against the paint."


def test_the_claim_function_itself_never_says_whole_court_with_unverified_lines():
    """Defensive: even a block that bypassed normalize_camera."""
    c = setup_state.camera_lock_claim({"lock_scope": "whole_court",
                                       "lock_unverified": ["far_service"]})
    assert "Every court line" not in c and "far_service" in c
