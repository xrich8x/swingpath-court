"""A stamped calibration must not break the paths that load it raw.

A calibration JSON is not only landmarks. The Court Setup tool writes `_exact`
when the user placed corners with shape-lock off; `validate_new_clip.py --stamp`
writes `_audit` with the camera verdict. Both are inert markers the pipeline
strips.

`pipeline.calibrate_video` had always stripped them. FIVE other callers did not --
run.py, live_demo.py, show_in_action.py, build_court_dataset.py and calibrate.py
all pass `json.load(f)` straight to `homography_from_landmarks` -- so a stamped
file raised `KeyError: '_audit'` and took the whole live line-call path with it.
The filter lived in one caller and five were missing it: trap T15's shape.

Found by running mobile/verify_live.js, whose Python reference invocation
(`live_demo.py replay --keypoints ../data/court_pts_refined.json`) crashed on a
file that had since been stamped.
"""

import json

import numpy as np
import pytest

from swingvision import calibration, court

CORNERS = {
    "near_bl_doubles": [100.0, 400.0],
    "near_br_doubles": [540.0, 400.0],
    "far_br_doubles": [420.0, 200.0],
    "far_bl_doubles": [220.0, 200.0],
}


def test_audit_and_exact_keys_are_skipped():
    stamped = dict(CORNERS)
    stamped["_exact"] = True
    stamped["_audit"] = {"verdict": "PASS", "fit_px": 0.4}
    H = calibration.homography_from_landmarks(stamped)
    assert H.shape == (3, 3)
    assert np.isfinite(H).all()


def test_the_stamp_changes_nothing_about_the_result():
    """Skipping metadata must be a no-op on the geometry, not merely non-fatal."""
    plain = calibration.homography_from_landmarks(dict(CORNERS))
    stamped = dict(CORNERS)
    stamped["_audit"] = {"verdict": "LOW-CAMERA"}
    stamped["_exact"] = True
    assert np.array_equal(plain, calibration.homography_from_landmarks(stamped))


def test_an_unknown_NON_metadata_key_still_raises():
    """The filter must not swallow a typo'd landmark name -- that should be loud."""
    bad = dict(CORNERS)
    bad["near_bl_doubels"] = [1.0, 2.0]        # transposed letters
    with pytest.raises(KeyError):
        calibration.homography_from_landmarks(bad)


def test_every_committed_calibration_loads():
    """The real files, since they are what the CLI is pointed at. Any *_pts.json
    the repo ships must be loadable by the path `run.py live` uses."""
    from pathlib import Path

    data = Path(__file__).resolve().parents[2] / "data"
    files = sorted(data.glob("*_pts*.json"))
    if not files:
        pytest.skip("no calibrations present")
    checked = 0
    for p in files:
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        names = [k for k in raw if not k.startswith("_")]
        if not all(n in court.LANDMARKS for n in names) or len(names) < 4:
            continue          # not a landmark file (e.g. an auto//other schema)
        H = calibration.homography_from_landmarks(raw)
        assert np.isfinite(H).all(), p.name
        checked += 1
    assert checked >= 5, f"only {checked} calibrations exercised"
