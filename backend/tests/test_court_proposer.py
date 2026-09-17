"""The court GLOBAL-PROPOSAL flag: `auto_fit_frame(..., proposer=...)`.

The three-stage recipe is GLOBAL localisation -> LOCAL refinement -> 6-DOF lock.
The flag switches stage one ONLY; stages two and three, and the consensus vote,
must be the same code for both arms or the A/B is not one variable.

What this pins:
  * the shipped default is unchanged - `auto_fit_frame(frame, ...)` and
    `auto_fit_frame(frame, ..., proposer="classical")` return the SAME court
    (the refactor-changed-nothing proof, rule 8);
  * an unknown proposer raises rather than silently falling back to the shipped
    one, because a silent fallback would report a CourtNet arm that never ran;
  * `resolved_proposer` reads the RESOLVED value (argument > env > default), so a
    provenance stamp cannot record a preset that did not run;
  * `resolved_courtnet_weights` mirrors detect_court_learned's own preference for
    `courtnet_ft.pt`, so an eval asking for the upstream checkpoint can DETECT
    that it would be handed our fine-tune instead (17 of 20 gold clips were in
    that model's training pool - scoring against it would be self-grading);
  * the courtnet arm feeds its proposal through the SAME snap+lock as the
    classical arm - checked with a stub detector, so the test needs no torch, no
    weights and no clip.

Synthetic court, same construction as test_auto_fit_with_score.py.
"""

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from swingvision import calibration, court, courtfit

_DBL = ("near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles")
_TRUE_IMG = {
    "near_bl_doubles": [150.0, 330.0], "near_br_doubles": [490.0, 330.0],
    "far_br_doubles": [400.0, 90.0], "far_bl_doubles": [240.0, 90.0],
}


def _true_h():
    return calibration.compute_homography(
        [court.LANDMARKS[n] for n in _DBL], [_TRUE_IMG[n] for n in _DBL])


def _court_frame(w=640, h=360):
    H = _true_h()
    frame = np.full((h, w, 3), 40, np.uint8)
    for a, b in court.LINES:
        pa = calibration.court_to_image(H, [a])[0]
        pb = calibration.court_to_image(H, [b])[0]
        cv2.line(frame, (int(round(pa[0])), int(round(pa[1]))),
                 (int(round(pb[0])), int(round(pb[1]))), (245, 245, 245), 2)
    return frame


class _StubCalibration:
    """`calibration` with ONLY detect_court_learned replaced. Everything else -
    snap_to_lines, lock_quad's helpers, the homography maths - is the real module,
    so the stub swaps the global proposal and nothing else."""

    def __init__(self, detection):
        self._detection = detection

    def __getattr__(self, name):
        return getattr(calibration, name)

    def detect_court_learned(self, frame, weights=None, device="cpu",
                             min_points=6, verify=True):
        return self._detection


def test_default_matches_explicit_classical():
    frame = _court_frame()
    default = courtfit.auto_fit_frame(frame, calibration, court)
    explicit = courtfit.auto_fit_frame(frame, calibration, court, proposer="classical")
    assert (default is None) == (explicit is None)
    if default is not None:
        for n in _DBL:
            assert default[n] == pytest.approx(explicit[n], abs=1e-9)


def test_unknown_proposer_raises():
    frame = _court_frame()
    with pytest.raises(ValueError):
        courtfit.auto_fit_frame(frame, calibration, court, proposer="cnn")


def test_resolved_proposer_prefers_argument_then_env(monkeypatch):
    monkeypatch.delenv("COURT_PROPOSER", raising=False)
    assert courtfit.resolved_proposer() == "classical"
    assert courtfit.resolved_proposer("courtnet") == "courtnet"
    monkeypatch.setenv("COURT_PROPOSER", "courtnet")
    assert courtfit.resolved_proposer() == "courtnet", "env must be readable by the eval"
    assert courtfit.resolved_proposer("classical") == "classical", "argument wins"


def test_resolved_weights_expose_the_finetune_substitution(monkeypatch, tmp_path):
    monkeypatch.delenv("COURTNET_WEIGHTS", raising=False)
    base = tmp_path / "court_detector.pt"
    base.write_bytes(b"")
    assert courtfit.resolved_courtnet_weights(str(base)) == str(base)
    ft = tmp_path / "courtnet_ft.pt"
    ft.write_bytes(b"")
    got = courtfit.resolved_courtnet_weights(str(base))
    assert got == str(ft), "the seam silently prefers the fine-tune; the eval must see that"
    monkeypatch.setenv("COURTNET_WEIGHTS", str(base))
    assert courtfit.resolved_courtnet_weights(str(base)) == str(base)


def test_courtnet_refusal_propagates():
    frame = _court_frame()
    stub = _StubCalibration(None)
    assert courtfit.auto_fit_frame(frame, stub, court, proposer="courtnet") is None
    assert courtfit.auto_fit_frame(frame, stub, court, proposer="courtnet",
                                   with_score=True) == (None, None)


def test_courtnet_proposal_runs_the_same_snap_and_lock():
    """A perfect CNN proposal on a synthetic court must survive stages two and
    three and come back near the truth - proving the flipped arm is wired through
    the shipped refinement and gate, not around them."""
    frame = _court_frame()
    det = calibration.CourtDetection(keypoints={}, homography=_true_h(), confidence=1.0)
    out = courtfit.auto_fit_frame(frame, _StubCalibration(det), court, proposer="courtnet")
    assert out is not None, "the shipped 6-DOF lock rejected an exact court"
    for n in _DBL:
        assert out[n] == pytest.approx(_TRUE_IMG[n], abs=8.0)


def test_courtnet_score_pairs_with_the_court():
    frame = _court_frame()
    det = calibration.CourtDetection(keypoints={}, homography=_true_h(), confidence=0.5)
    stub = _StubCalibration(det)
    plain = courtfit.auto_fit_frame(frame, stub, court, proposer="courtnet")
    corners, score = courtfit.auto_fit_frame(frame, stub, court, proposer="courtnet",
                                             with_score=True)
    assert not isinstance(plain, tuple)
    assert score == pytest.approx(0.5)
    for n in _DBL:
        assert plain[n] == pytest.approx(corners[n], abs=1e-9)
