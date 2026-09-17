"""The browser's copies of Python constants must not drift.

Two tables are duplicated by hand into JavaScript so the dashboard can use them
without a backend call:

    backend/swingvision/court.py        -> frontend/src/lib/court.js
    backend/swingvision/calibration.py  -> frontend/src/lib/calls.js

Until now BOTH were guarded by a comment saying "keep these in sync" and by
nothing else. The frontend has no test runner, so there was no side this could
be checked from - which is exactly the shape of Trap T06: a discipline enforced in
one place is not enforced across the project. The failure is silent and ugly:
someone corrects a number in Python, every backend test passes, and the
dashboard quietly keeps showing last month's value to the user.

These tests read the JS as text from the Python side. No Node, no new toolchain
- the JS is parsed and its arithmetic evaluated, so DERIVED constants
(ALLEY, NET_Y, X_*, Y_*) are compared as values rather than as source strings,
and a formula that drifts is caught as well as a literal that does.

NOT covered: a change to the JS interpolation FUNCTION itself (only its table is
compared). That was verified by hand against Python at 17 heights when calls.js
was written, including both clamp ends.
"""

import re
from pathlib import Path

import pytest

from swingvision import calibration, court

_FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib"
_COURT_JS = _FRONTEND / "court.js"
_CALLS_JS = _FRONTEND / "calls.js"

# `export const NAME = <expr>;` - expr captured up to the first semicolon.
_EXPORT_RE = re.compile(r"^export const ([A-Z_][A-Z0-9_]*)\s*=\s*([^;]+);", re.M)
# Only plain arithmetic over numbers and earlier ALL_CAPS names is evaluated;
# anything else (arrays, objects, functions) is skipped by this filter.
_ARITH_RE = re.compile(r"^[0-9_.+\-*/() A-Z]+$")


def _js_numeric_consts(path: Path) -> dict:
    """Every `export const` in `path` whose value is plain arithmetic, evaluated
    in declaration order so later constants can reference earlier ones."""
    src = path.read_text(encoding="utf-8")
    out: dict = {}
    for name, expr in _EXPORT_RE.findall(src):
        expr = expr.split("//")[0].strip()
        if not _ARITH_RE.match(expr):
            continue
        try:
            out[name] = float(eval(expr, {"__builtins__": {}}, dict(out)))
        except Exception:
            continue
    return out


# ------------------------------------------------------------------ court.js

def test_court_js_files_exist():
    assert _COURT_JS.is_file(), f"missing {_COURT_JS}"
    assert _CALLS_JS.is_file(), f"missing {_CALLS_JS}"


def test_court_js_mirrors_court_py():
    js = _js_numeric_consts(_COURT_JS)
    assert js, "parsed no numeric constants out of court.js - has its format changed?"

    checked = []
    for name, js_val in sorted(js.items()):
        py_val = getattr(court, name, None)
        if py_val is None or not isinstance(py_val, (int, float)):
            continue
        assert js_val == pytest.approx(float(py_val), abs=1e-9), (
            f"court.js {name} = {js_val} but court.py {name} = {py_val}. "
            f"The dashboard is drawing a different court than the analyzer.")
        checked.append(name)

    # Guard the guard: if a rename made the intersection empty this test would
    # pass while comparing nothing.
    assert len(checked) >= 12, f"only compared {checked} - the mirror check has gone blind"
    for essential in ("LENGTH", "DOUBLES_WIDTH", "SINGLES_WIDTH",
                      "SERVICE_LINE_FROM_NET", "NET_Y"):
        assert essential in checked, f"{essential} was not compared"


def test_court_constants_are_regulation():
    """The mirror could agree and both be wrong. These are fixed by the rules of
    tennis, so they are checkable against the world rather than against us."""
    assert court.LENGTH == 23.77
    assert court.DOUBLES_WIDTH == 10.97
    assert court.SINGLES_WIDTH == 8.23
    assert court.SERVICE_LINE_FROM_NET == 6.40
    assert court.NET_Y == pytest.approx(11.885)


# ------------------------------------------------------------------ calls.js

def _js_call_table() -> list:
    src = _CALLS_JS.read_text(encoding="utf-8")
    m = re.search(r"const CALL_ACCURACY_BY_HEIGHT\s*=\s*\[(.*?)\];", src, re.S)
    assert m, "could not find CALL_ACCURACY_BY_HEIGHT in calls.js"
    pairs = re.findall(r"\[\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\]", m.group(1))
    return [(float(a), float(b)) for a, b in pairs]


def test_calls_js_table_mirrors_calibration_py():
    js_tbl = _js_call_table()
    py_tbl = [(float(z), float(a)) for z, a in calibration._CALL_ACCURACY_BY_HEIGHT]
    assert js_tbl == py_tbl, (
        "the height/accuracy table in calls.js has drifted from calibration.py - "
        "the dashboard is quoting different line-call accuracy than the CLI")


def test_calls_js_floor_mirrors_calibration_py():
    src = _CALLS_JS.read_text(encoding="utf-8")
    m = re.search(r"export const CALL_MAJORITY_FLOOR_PCT\s*=\s*([0-9.]+);", src)
    assert m, "CALL_MAJORITY_FLOOR_PCT not found in calls.js"
    assert float(m.group(1)) == pytest.approx(calibration.CALL_MAJORITY_FLOOR_PCT), (
        "the majority-class floor differs between the dashboard and Python. This "
        "is the number that decides whether a mount is worth anything at all.")


def test_python_interpolation_agrees_with_the_js_table():
    """Cross-check the shipped Python function against the table the BROWSER
    holds, at every knot and between them, including both clamp ends."""
    tbl = _js_call_table()

    def js_style_interp(z):
        if z <= tbl[0][0]:
            return tbl[0][1]
        if z >= tbl[-1][0]:
            return tbl[-1][1]
        for (z0, a0), (z1, a1) in zip(tbl, tbl[1:]):
            if z0 <= z <= z1:
                return a0 + (a1 - a0) * (z - z0) / (z1 - z0)
        return tbl[-1][1]

    heights = [0.5, 20.0]                                  # both clamps
    heights += [z for z, _ in tbl]                         # every knot
    heights += [1.37, 1.38, 1.74, 3.21, 3.5, 7.0, 10.0]    # real + between-knot
    for z in heights:
        assert calibration.expected_call_accuracy(z) == pytest.approx(
            js_style_interp(z), abs=1e-9), f"Python and the JS table disagree at {z} m"
