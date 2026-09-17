"""The COURT TEST/TRAIN split must stay disjoint, and stay honest.

Before data/gold/court_split.json existed, 17 of the 20 hand-labelled court gold
clips were also in data/court_dataset/ and train_courtnet.py had no leak guard —
so every figure in data/gold/court_scores.md was the model scored on its own
training data. This pins the fix.

Two independent sources of truth have to agree, and that is deliberate:
  - the MANIFEST says which clips are TEST,
  - the FILESYSTEM says which clips the trainer can actually see.
The second is the stronger guarantee (you cannot train on what is not there), so
the test asserts the manifest is not quietly claiming protection the directory
layout does not provide. tools/eval_court.py derives held-out from the same
directory state, so a drift between the two would silently mislabel the split.
"""

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

import train_courtnet as tc

MANIFEST = REPO / "data" / "gold" / "court_split.json"
TRAIN_ROOT = REPO / "data" / "court_dataset"


def _manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_exists_and_declares_both_sides():
    m = _manifest()
    assert m["test"]["clips"], "no TEST clips declared"
    assert m["train"]["clips"], "no TRAIN clips declared"


def test_test_and_train_are_disjoint():
    m = _manifest()
    test = set(m["test"]["clips"])
    train = set(m["train"]["clips"])
    assert not (test & train), f"clip declared both TEST and TRAIN: {sorted(test & train)}"


def test_no_test_clip_sits_in_the_training_root():
    """The load-bearing assertion. If this fails, the trainer can see the benchmark."""
    if not TRAIN_ROOT.is_dir():
        return              # dataset not present on this machine; nothing to check
    present = {p.name for p in TRAIN_ROOT.iterdir()
               if (p / "labels.json").is_file()}
    leaked = sorted(set(tc.court_test_clips()) & present)
    assert not leaked, (
        f"TEST clips present in {TRAIN_ROOT}: {leaked}. "
        "Every court number would be self-grading again.")


def test_guard_refuses_a_root_containing_a_test_clip(tmp_path):
    """The guard must RAISE, not warn. Build a fake training root holding one
    TEST clip and confirm it refuses."""
    import pytest

    leak = tmp_path / tc.court_test_clips()[0]
    leak.mkdir()
    (leak / "labels.json").write_text('{"labels": {}}', encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        tc.assert_no_court_gold_leak(str(tmp_path))
    assert "REFUSING TO TRAIN" in str(e.value)


def test_guard_passes_a_clean_root(tmp_path):
    ok = tmp_path / "not_a_gold_clip"
    ok.mkdir()
    (ok / "labels.json").write_text('{"labels": {}}', encoding="utf-8")
    missing = tc.assert_no_court_gold_leak(str(tmp_path))
    assert set(missing) == set(tc.court_test_clips())


def test_every_test_clip_has_gold_labels_to_score_against():
    """A TEST clip with no human labels is not a benchmark, it is a gap."""
    for clip in tc.court_test_clips():
        p = REPO / "data" / "gold" / f"{clip}.court.labels.json"
        assert p.is_file(), f"{clip} is declared TEST but has no court gold labels"
        labels = json.loads(p.read_text(encoding="utf-8"))["labels"]
        usable = sum(1 for v in labels.values() if v.get("court") is True)
        assert usable >= 10, f"{clip}: only {usable} usable frames — too thin for TEST"
