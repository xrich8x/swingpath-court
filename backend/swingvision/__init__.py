"""swingvision — single-camera tennis match analyzer.

Pipeline stages, one module each (see CLAUDE.md for the perception / geometry /
logic boundary that is the architecture):

    court        court constants + landmarks            (geometry)
    calibration  homography solve + keypoint stub       (geometry / ML)
    pose         player pose                            (ML stub)
    ball         TrackNet stub + trajectory smoothing   (ML / physics)
    events       hits, bounces, rallies, shot type
    analytics    shot speed + line calls                (geometry)
    scoring      tennis scoring state machine           (logic)
    pipeline     orchestrator + synthetic demo
    schema       the match.json contract
"""

__version__ = "0.1.0"
