"""Recording identity must come from the SOURCE VIDEO, never from a clip name.

The bug this pins: the 20 court gold clips and the 54-recording eval drop set were
reported all session as independent populations, and 9 of the 20 gold clips are
drop recordings under another name. `am_rally32short` IS `yt_tnxkujogch4.mp4`.
A gate gain and a breadth gain were counted as separate evidence when they were the
same file.

That is trap T17 on the evaluation side - "trimming a clip renames it, and the guard
matches on the NAME". The gold manifests record `video`; nothing read it.

These tests fail if anyone reintroduces name-based identity, or quietly drops the
manifest field the fix depends on.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "eval"

pytestmark = pytest.mark.skipif(
    not (EVAL / "recordings.py").exists() or not (REPO / "data" / "gold").exists(),
    reason="eval harness or gold set not present")


@pytest.fixture(scope="module")
def rec():
    sys.path.insert(0, str(EVAL))
    import recordings
    return recordings


def test_the_known_alias_resolves_to_one_recording(rec):
    """am_rally32short's manifest names yt_tnxkujogch4.mp4 as its source, so the
    two must share a recording key. This exact pair is what exposed the bug."""
    gold = rec.gold_sources()
    assert "am_rally32short" in gold, "gold clip missing - check the manifest glob"
    assert gold["am_rally32short"]["key"] == "tnxkujogch4"
    assert rec.overlap().get("am_rally32short") == "tnxkujogch4"


def test_overlap_is_reported_not_silently_merged(rec):
    """The overlap must be visible. Silently merging the populations would hide the
    double-count instead of surfacing it, which is how it survived this long."""
    ov = rec.overlap()
    assert ov, "no overlap detected - identity has regressed to clip names"
    assert len(ov) >= 9
    for gold_clip, drop_group in ov.items():
        assert gold_clip != drop_group, "an alias must map ACROSS names, not to itself"


def test_independent_subset_excludes_every_shared_recording(rec):
    """The honest denominator for any drop-set claim offered as evidence beyond
    the gate."""
    ind = set(rec.independent_drop_groups())
    shared = set(rec.overlap().values())
    assert ind.isdisjoint(shared)
    assert len(ind) == len(rec.drop_keys()) - len(shared)


def test_streamed_gold_clips_have_no_local_key(rec):
    """A clip captured from a YouTube stream has no local file, so it cannot
    collide with the drop set and must not be given a key that pretends it might."""
    gold = rec.gold_sources()
    streamed = [c for c, v in gold.items() if v["source"] == "youtube-stream"]
    assert streamed, "expected some streamed gold clips"
    for c in streamed:
        assert gold[c]["key"] is None
