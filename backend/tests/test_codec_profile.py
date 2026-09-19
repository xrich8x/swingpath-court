"""G8 Part B: the CP1 encoder profile is UNMOVED, and the deterministic one is
pinned. These pin the ffmpeg argv, not a measured number - the repeat-run equality
is in docs/evidence/court-camera3d.md, G8.

qa isolated CP1's run-to-run scatter to the encoder itself (audit 2026-09-18 s6).
Changing CRF/preset/keyint changes the SCENE, so the pin is a SECOND named profile,
never an edit of the first.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
T = pytest.importorskip("court_fit_cp1")


# The literal argv the pre-G8 code built, transcribed from tools/court_fit_cp1.py
# at commit 6391d01. If this test fails, a CP1/G1/G7 number has silently moved.
def _pre_g8_argv(fn):
    X = T.X265
    return ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "yuv420p",
            "-s", f"{T.W}x{T.H}", "-r", str(X["fps"]), "-i", "-", "-c:v", "libx265",
            "-profile:v", X["profile"], "-preset", X["preset"], "-b:v", X["bitrate"],
            "-x265-params", (f"keyint={X['keyint']}:min-keyint={X['keyint']}:"
                             f"vbv-maxrate={X['vbv_maxrate_kbps']}:"
                             f"vbv-bufsize={X['vbv_bufsize_kbps']}:log-level=error"),
            "-pix_fmt", "yuv420p", str(fn)]


def test_the_cp1_profile_encodes_exactly_as_before():
    assert T._encode_argv(T.X265, "clip.hevc") == _pre_g8_argv("clip.hevc")


def test_the_cp1_profile_is_still_the_default():
    assert T.CODEC_PROFILES["cp1"] is T.X265
    assert T.stamp("P", 1, 0, 1)["codec_profile"] == "cp1"


def test_the_deterministic_profile_pins_the_thread_count():
    argv = T._encode_argv(T.X265_DETERMINISTIC, "clip.hevc")
    params = argv[argv.index("-x265-params") + 1]
    assert "pools=1" in params and "frame-threads=1" in params and "wpp=0" in params
    assert "keyint=1:min-keyint=1" in params
    assert argv[argv.index("-threads") + 1] == "1"
    assert "-crf" in argv and "-b:v" not in argv        # CRF, no VBV lookahead state


def test_the_deterministic_profile_says_it_is_not_comparable():
    assert "NOT_COMPARABLE_WITH" in T.X265_DETERMINISTIC


def test_the_stamp_reads_the_resolved_profile_not_a_preset_table():
    s = T.stamp("P", 1, 0, 1, "deterministic")
    assert s["codec_profile"] == "deterministic"
    assert s["codec"]["crf"] == 18 and s["codec"]["preset"] == "slow"


def test_an_arm_with_no_codec_stamps_no_profile():
    s = T.stamp("A3", 1, 0, 1, "deterministic")
    assert s["codec"] is None and s["codec_profile"] is None
