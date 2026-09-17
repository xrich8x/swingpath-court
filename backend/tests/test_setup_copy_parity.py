"""The user-facing setup copy is a CONTRACT, and it lives in two languages.

`backend/swingvision/setup_state.py` owns the strings; `frontend/src/lib/setup.js`
is the copy the browser reads. The frontend has no test runner, so — exactly as
with court.js and calls.js (test_js_mirror_parity.py) — the only side this can be
checked from is Python.

WHY THIS IS WORTH A TEST RATHER THAN A COMMENT. The strings are not decoration.
A user is being told that their recording is usable but that some of its numbers
are not verified. If the CLI says one thing, the dashboard says another and the
phone app says a third, the limitation stops reading as a fact about the setup
and starts reading as a glitch — and the honest version is the one people ignore.
Both files already carry "keep these in sync" comments; that is precisely the
guard that failed for court.js before test_js_mirror_parity.py existed.

NOT covered: the JS `trustPolicy` presentation rules (which state shows which
banner). Those are frontend policy with no Python counterpart, and inventing a
Python mirror of them purely to have something to compare against would create a
second source of truth for a decision only the UI makes.
"""

import re
from pathlib import Path

import pytest

from swingvision import setup_state as ss

_SETUP_JS = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib"
             / "setup.js")


def _js_source() -> str:
    if not _SETUP_JS.is_file():
        pytest.skip(f"{_SETUP_JS} not present")
    return _SETUP_JS.read_text(encoding="utf-8")


def _js_string_const(src: str, name: str) -> str:
    """Value of `export const NAME = "..." + "..." ;` with the pieces joined.

    The JS wraps long copy across concatenated literals for line length. Joining
    them here compares the STRING, not its line breaks — a re-wrap must not fail
    this test and a changed word must.
    """
    m = re.search(rf"^export const {name}\s*=\s*(.*?);\s*$", src,
                  re.M | re.S)
    assert m, f"{name} not found in setup.js"
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
    assert parts, f"{name} in setup.js is not a string literal"
    return "".join(p.encode().decode("unicode_escape") for p in parts)


def _js_string_array(src: str, name: str) -> list:
    m = re.search(rf"^export const {name}\s*=\s*\[(.*?)\];\s*$", src, re.M | re.S)
    assert m, f"{name} not found in setup.js"
    return [p.encode().decode("unicode_escape")
            for p in re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))]


@pytest.mark.parametrize("py_name,js_name", [
    ("LOW_CAMERA_TITLE", "LOW_CAMERA_TITLE"),
    ("LOW_CAMERA_BODY", "LOW_CAMERA_BODY"),
    ("OVERLAP_TITLE", "OVERLAP_TITLE"),
    ("OVERLAP_BODY", "OVERLAP_BODY"),
    ("CLEAR_SUMMARY", "CLEAR_SUMMARY"),
    ("UNKNOWN_SUMMARY", "UNKNOWN_SUMMARY"),
    ("FAR_BASELINE_QUESTION", "FAR_BASELINE_QUESTION"),
])
def test_copy_is_identical_in_both_languages(py_name, js_name):
    assert _js_string_const(_js_source(), js_name) == getattr(ss, py_name), (
        f"{py_name} has drifted between setup_state.py and setup.js")


def test_the_three_actions_match_in_order():
    """Order matters: 'Continue with this setup' must be FIRST, because
    continuing is always allowed and the first action is the one people take."""
    js = _js_string_array(_js_source(), "FRAMING_ACTIONS")
    assert js == list(ss.FRAMING_ACTIONS)
    assert js[0] == "Continue with this setup"


def test_the_status_vocabularies_match():
    src = _js_source()
    for name in ss.FRAMING_STATUSES:
        assert f'"{name}"' in src, f"framing status {name!r} missing from setup.js"
    for name in ss.CALIBRATION_STATUSES:
        assert f'"{name}"' in src, f"calibration status {name!r} missing from setup.js"


def test_the_exact_low_camera_copy_is_the_specified_copy():
    """The two notices were specified word-for-word by the product brief. Pinning
    them here means a later 'tidy-up' of the wording is a deliberate act with a
    failing test attached, not a silent edit."""
    assert ss.LOW_CAMERA_TITLE == (
        "Camera is a little low for precise court measurements")
    assert ss.LOW_CAMERA_BODY == (
        "You can continue recording. Video review, rally clips, highlights, and "
        "manual corrections will still work. For more reliable speed, bounce "
        "locations, and line calls, raise the phone until the far baseline is "
        "clearly visible below the net.")
    assert ss.OVERLAP_TITLE == "The net hides the far baseline"
    assert ss.OVERLAP_BODY == (
        "You can still record and review this match. Court measurements may be "
        "less reliable, especially on the far half. Raising the phone gives "
        "better results.")


def test_neither_notice_ever_tells_the_user_to_stop():
    """The one property the copy exists to have. A low camera is a measured limit
    on what the image contains, not a user error - so no notice may read as a
    refusal, and both must say what still works."""
    for status in (ss.FRAMING_LIMITED, ss.FRAMING_OVERLAP):
        n = ss.notice_for(status)
        body = n["body"].lower()
        assert "you can" in body, f"{status}: does not tell the user they may continue"
        for banned in ("cannot record", "not supported", "unsupported",
                       "please re-record", "must raise", "required"):
            assert banned not in body, f"{status}: reads as a refusal ({banned!r})"
        assert n["actions"][0] == "Continue with this setup"
