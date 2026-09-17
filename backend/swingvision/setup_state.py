"""setup_state.py — the persisted trust state: what this camera setup can honestly claim.

WHY THIS EXISTS
---------------
`calibration.net_tape_clearance` already measures, in pixels, whether the far
baseline is separable from the net tape (docs/evidence/live-setup-criterion.md).
It is guidance and it is transient: it is printed by `run.py check`, shown in the
setup tool, and then thrown away. Nothing downstream — not `match.json`, not the
dashboard, not a corrections replay — could say afterwards whether the numbers it
is rendering came from a setup where the information was in the image at all.

So a user with a phone on a tripod got the same confident speeds, bounce map and
line calls as a user with the phone clamped 3 m up a fence. **16 of the 28 real
calibrations in this repo (57%) are below the crossover**, so that is the normal
case, not the edge case. This module is the state that travels with the match and
lets every surface downstream tell the difference.

THE THREE THINGS IT RECORDS, AND WHY THEY ARE SEPARATE AXES
-----------------------------------------------------------
1. `framing_status` — is the far baseline separable from the net tape?
   GEOMETRY. Derived from the clearance margin, or from the user's own answer
   before any calibration exists. clear | limited | overlap | unknown.
2. `calibration_status` — did a human confirm the four corners, or did software
   place them? PROVENANCE. user_confirmed | provisional | unavailable.
   These are independent: a 3 m mount with an unconfirmed auto-detected court is
   `clear` + `provisional`, and a hand-confirmed 1.4 m tripod is `overlap` +
   `user_confirmed`. Collapsing them into one "quality" score would hide which
   of the two a user can actually fix.
3. `metrics_eligible` — may court-derived numbers be presented as VERIFIED?
   Only when both of the above are good. This is a claim about presentation, NOT
   a gate: nothing here stops a metric being computed, stored or displayed, and
   nothing here refuses a recording. See "NOT A GATE" below.

WHY `user_confirmed` IS NARROW
------------------------------
Trap T26: `_exact` in a keypoints file was read downstream as "a human
deliberately placed these corners" and it never meant that — it meant the setup
tool's Shape lock checkbox happened to be off. An agent driving the tool produced
a file indistinguishable from a person's, and the founder later marked 10 of 28
committed placements wrong. So `user_confirmed` here requires an EXPLICIT
confirmation stamp written at the moment a human said "yes, those four corners
are on the court corners" (`_provenance.confirmed_by_user`), or a real
attribution in `_provenance.placed_by`. Everything else — every auto-detected
court, and every hand-placed file that predates the stamp — is `provisional`.
That is a statement about the chain of custody, not an accusation about the
clicks.

NOT A GATE
----------
Five autonomous accept/reject gates have failed on this project, and the
clearance criterion was deliberately built as the sixth thing that is NOT one.
This module inherits that: it returns a state and some sentences, never a
refusal. `metrics_eligible=False` means "do not render this as a verified fact",
never "do not record", "do not analyze" or "do not show". A caller that turns any
field here into a refusal has changed its kind, and this paragraph is the record
that it was not built that way.

BACKWARDS COMPATIBILITY
-----------------------
Every match.json written before this module has no `setup` block. `normalize()`
turns a missing or partial block into a fully-populated `unknown` state, so an
older file loads and renders — it simply cannot claim anything. `unknown` is a
third thing, distinct from both "verified" and "limited": we do not know, and the
UI must not invent either answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

# --- the vocabulary -------------------------------------------------------
FRAMING_CLEAR = "clear"
FRAMING_LIMITED = "limited"
FRAMING_OVERLAP = "overlap"
FRAMING_UNKNOWN = "unknown"
FRAMING_STATUSES = (FRAMING_CLEAR, FRAMING_LIMITED, FRAMING_OVERLAP,
                    FRAMING_UNKNOWN)

CALIB_USER_CONFIRMED = "user_confirmed"
CALIB_PROVISIONAL = "provisional"
CALIB_UNAVAILABLE = "unavailable"
CALIBRATION_STATUSES = (CALIB_USER_CONFIRMED, CALIB_PROVISIONAL,
                        CALIB_UNAVAILABLE)

#: `calibration.NetClearance.level` -> framing_status. The bands themselves were
#: pre-registered before the clip sweep and are NOT re-tuned here: good >= +10 px
#: @720p, marginal 0..+10, poor <= 0 (docs/evidence/live-setup-criterion.md).
#: This map only renames them into product language.
_LEVEL_TO_FRAMING = {
    "good": FRAMING_CLEAR,
    "marginal": FRAMING_LIMITED,
    "poor": FRAMING_OVERLAP,
}

# --- the exact user-facing copy -------------------------------------------
# These strings are a CONTRACT, mirrored verbatim in frontend/src/lib/setup.js
# and pinned by backend/tests/test_setup_copy_parity.py. Change one, change both,
# in the same commit. They are deliberately written as "you can continue" first
# and "here is how to improve it" second: a low mount is a measured limitation of
# what the image contains, not a user error, and never a reason to refuse a
# recording.
LOW_CAMERA_TITLE = "Camera is a little low for precise court measurements"
LOW_CAMERA_BODY = (
    "You can continue recording. Video review, rally clips, highlights, and "
    "manual corrections will still work. For more reliable speed, bounce "
    "locations, and line calls, raise the phone until the far baseline is "
    "clearly visible below the net."
)
OVERLAP_TITLE = "The net hides the far baseline"
OVERLAP_BODY = (
    "You can still record and review this match. Court measurements may be less "
    "reliable, especially on the far half. Raising the phone gives better results."
)
#: The same three actions serve both notices — continue, learn how, re-check —
#: and "Continue with this setup" is always FIRST because continuing is always
#: allowed.
FRAMING_ACTIONS = (
    "Continue with this setup",
    "Show me how to improve it",
    "Re-check framing",
)

#: Shown while framing is `clear`. Not a notice (nothing to fix), just the
#: sentence the Results UI uses to say the check actually happened.
CLEAR_SUMMARY = (
    "Framing verified: the far baseline is clearly separated from the net tape, "
    "so the court can be measured normally."
)
UNKNOWN_SUMMARY = (
    "Setup quality was not recorded for this match, so we cannot say how "
    "reliable the court measurements are."
)

#: The plain-English question asked BEFORE a calibration exists (Feature 1). The
#: clearance criterion needs a homography, and a live preview has none — so the
#: first version asks the person holding the phone, and records that the answer
#: came from a human rather than from geometry.
FAR_BASELINE_QUESTION = (
    "Looking at the far end of the court: can you see the far baseline as a "
    "separate line BELOW the top of the net?"
)


def notice_for(framing_status: str) -> Optional[dict]:
    """The title/body/actions to show for a framing status, or None.

    `clear` and `unknown` have no notice — there is nothing to warn about and
    nothing to fix. Returning None rather than an empty dict keeps "no notice"
    distinguishable from "a notice with no text".
    """
    if framing_status == FRAMING_LIMITED:
        return {"title": LOW_CAMERA_TITLE, "body": LOW_CAMERA_BODY,
                "actions": list(FRAMING_ACTIONS)}
    if framing_status == FRAMING_OVERLAP:
        return {"title": OVERLAP_TITLE, "body": OVERLAP_BODY,
                "actions": list(FRAMING_ACTIONS)}
    return None


def framing_from_level(level: Optional[str]) -> str:
    """clearance level (good|marginal|poor|None) -> framing_status."""
    return _LEVEL_TO_FRAMING.get(level or "", FRAMING_UNKNOWN)


def framing_from_user_answer(far_baseline_visible: Optional[bool]) -> str:
    """The user's own answer -> framing_status.

    True -> `clear`, False -> `overlap`, None/unsure -> `unknown`. There is
    deliberately no path from a human answer to `limited`: a person can see
    whether two lines are separate, but "separate by less than 10 px at 720p" is
    not a judgement anybody can make by eye. `limited` is reserved for the
    measured margin.
    """
    if far_baseline_visible is True:
        return FRAMING_CLEAR
    if far_baseline_visible is False:
        return FRAMING_OVERLAP
    return FRAMING_UNKNOWN


@dataclass
class SetupState:
    """What this match's camera setup can honestly claim. Serialised into
    match.json under `setup` (see schema.Match)."""

    #: clear | limited | overlap | unknown — is the far baseline separable?
    framing_status: str = FRAMING_UNKNOWN
    #: Pixels of daylight between the far baseline and the net tape at 720p.
    #: Positive = clear. None when it was never measured (no calibration, or no
    #: physical camera fits the quad).
    far_baseline_clearance_px_720: Optional[float] = None
    #: user_confirmed | provisional | unavailable — who placed the corners.
    calibration_status: str = CALIB_UNAVAILABLE
    #: May court-derived numbers be presented as VERIFIED facts? Never a gate.
    metrics_eligible: bool = False
    #: Plain-English sentences, rendered directly. Every one of them names the
    #: condition that produced it, so a user is never told "limited" with no why.
    reasons: list[str] = field(default_factory=list)
    # --- provenance of the state itself (extensions to the suggested shape) ---
    #: "clearance_geometry" | "user_answer" | "none". Which of the two routes in
    #: Feature 1 produced `framing_status`. A user's answer is guidance; the
    #: geometry is a measurement. Never let the UI present them as the same thing.
    framing_source: str = "none"
    #: What the user answered to FAR_BASELINE_QUESTION, if they were asked.
    #: Kept even after geometry supersedes it, so a disagreement stays visible.
    far_baseline_user_answer: Optional[bool] = None
    #: {title, body, actions} for `limited`/`overlap`, else None. Carried in the
    #: file so an export or a screenshot cannot lose the limitation, and so the
    #: iOS app and the web dashboard cannot drift into two different wordings.
    notice: Optional[dict] = None

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @property
    def limited(self) -> bool:
        """True when the UI must show a persistent limitation status."""
        return self.framing_status in (FRAMING_LIMITED, FRAMING_OVERLAP)


def build(*, clearance: Any = None,
          calibration_status: str = CALIB_UNAVAILABLE,
          far_baseline_user_answer: Optional[bool] = None,
          extra_reasons: Sequence[str] = ()) -> SetupState:
    """Assemble the trust state.

    `clearance` is a `calibration.NetClearance` (or None). Duck-typed rather than
    imported so this module stays free of numpy and cv2 — the iOS/mobile port and
    the tests both build states without a homography in hand.

    GEOMETRY WINS OVER THE ANSWER, and the disagreement is recorded rather than
    resolved silently: if the user said the far baseline was clear and the fitted
    court says the lines overlap, the state says `overlap` and carries a reason
    saying both. That is the honest ordering — the margin is measured from the
    corners the user themselves placed, while the answer was a glance at a
    preview.
    """
    reasons: list[str] = []
    px: Optional[float] = None
    framing = FRAMING_UNKNOWN
    source = "none"

    if far_baseline_user_answer is not None:
        framing = framing_from_user_answer(far_baseline_user_answer)
        source = "user_answer"
        reasons.append(
            "You told us the far baseline was clearly separate from the net."
            if far_baseline_user_answer else
            "You told us the net hides the far baseline.")

    if clearance is not None:
        px = round(float(clearance.margin_px_720), 1)
        geo = framing_from_level(getattr(clearance, "level", None))
        if geo != FRAMING_UNKNOWN:
            if (framing != FRAMING_UNKNOWN and framing != geo
                    and far_baseline_user_answer is not None):
                reasons.append(
                    f"Your answer and the fitted court disagree, so we used the "
                    f"measurement: the far baseline is {px:+.0f} px from the net "
                    f"tape at 720p.")
            framing = geo
            source = "clearance_geometry"
        if framing == FRAMING_OVERLAP:
            reasons.append(
                f"The net tape and the far baseline overlap in this view "
                f"({px:+.0f} px at 720p, where positive means clear), so no "
                f"measurement can tell them apart.")
        elif framing == FRAMING_LIMITED:
            reasons.append(
                f"Only {px:.0f} px separate the far baseline from the net tape "
                f"at 720p. The lines are separable but close, so far-court "
                f"positions carry real error.")
        elif framing == FRAMING_CLEAR:
            reasons.append(
                f"The far baseline is {px:.0f} px clear of the net tape at 720p.")
    elif far_baseline_user_answer is None:
        reasons.append(UNKNOWN_SUMMARY)

    if calibration_status not in CALIBRATION_STATUSES:
        calibration_status = CALIB_UNAVAILABLE
    # The generic sentence for the calibration axis is a FALLBACK. A caller that
    # supplies its own reason (calibration_status_from_keypoints, the camera-moved
    # branch in the pipeline) knows something more specific than "not confirmed",
    # and printing both reads as two separate problems when there is one.
    if not extra_reasons:
        if calibration_status == CALIB_UNAVAILABLE:
            reasons.append("No court calibration is attached to this match, so "
                           "nothing was projected to court metres.")
        elif calibration_status == CALIB_PROVISIONAL:
            reasons.append("The court corners have not been confirmed by a "
                           "person, so this calibration is provisional.")

    # BOTH axes must be good before a court-derived number is presented as a
    # verified fact. Framing alone is not enough (a perfectly framed but wrongly
    # placed court is trap T23, which passed a 0.9 px residual with all four
    # corners off the paint), and confirmation alone is not enough (confirming
    # corners does not put information into an image that never had it).
    eligible = (framing == FRAMING_CLEAR
                and calibration_status == CALIB_USER_CONFIRMED)

    reasons.extend(str(r) for r in extra_reasons)
    return SetupState(framing_status=framing,
                      far_baseline_clearance_px_720=px,
                      calibration_status=calibration_status,
                      metrics_eligible=eligible,
                      reasons=reasons,
                      framing_source=source,
                      far_baseline_user_answer=far_baseline_user_answer,
                      notice=notice_for(framing))


def from_homography(H, img_wh, *, calibration_status: str = CALIB_PROVISIONAL,
                    far_baseline_user_answer: Optional[bool] = None,
                    extra_reasons: Sequence[str] = ()) -> SetupState:
    """`build` straight from a homography — the pipeline/CLI entry point.

    Imports `calibration` lazily so importing this module stays cheap and
    dependency-free for anything that only needs the vocabulary and the copy.
    """
    from . import calibration as _cal

    clr = _cal.net_tape_clearance(H, img_wh)
    return build(clearance=clr, calibration_status=calibration_status,
                 far_baseline_user_answer=far_baseline_user_answer,
                 extra_reasons=extra_reasons)


def calibration_status_from_keypoints(raw: Optional[dict], source: str) -> tuple[str, list[str]]:
    """(calibration_status, reasons) for a calibration the pipeline just used.

    `raw` is the keypoints JSON as loaded (including its `_` metadata), or None
    when the court was auto-detected. `source` is `calibrate_video`'s source tag
    ("manual", "manual-exact", "auto-court(7/8)", "learned", ...).

    THE RULE, and it is deliberately conservative (trap T26): only an EXPLICIT
    confirmation counts. `_provenance.confirmed_by_user` is written the moment a
    person ticks the four named corners in the setup flow; `_provenance.placed_by`
    counts when it names somebody other than the honest default "unattributed".
    `_exact` does NOT count and never did — it only ever meant the Shape lock
    checkbox was off.
    """
    if not source:
        return CALIB_UNAVAILABLE, []
    prov = (raw or {}).get("_provenance") or {}
    placed_by = str(prov.get("placed_by") or "").strip().lower()
    if prov.get("confirmed_by_user") is True:
        return CALIB_USER_CONFIRMED, []
    if placed_by and placed_by not in ("unattributed", "unknown", "auto", "agent"):
        return CALIB_USER_CONFIRMED, []
    if raw is not None:
        return CALIB_PROVISIONAL, [
            "These corners came from a keypoints file with no record of a person "
            "confirming them, so they are treated as provisional."]
    return CALIB_PROVISIONAL, [
        f"The court was detected automatically ({source}) and nobody has "
        f"confirmed the corners."]


def normalize(raw: Any) -> dict[str, Any]:
    """Coerce whatever a match.json carries under `setup` into the full shape.

    THE BACKWARDS-COMPATIBILITY CONTRACT. A match.json written before this block
    existed has no `setup` key at all; one written by an older/newer version may
    have a partial one, or a status string this build does not know. All three
    load as a well-formed `unknown` state rather than raising — an old match must
    still open, and an unreadable trust state must degrade to "we do not know",
    never to "verified".

    Never returns None, never raises, never invents a `clear`.
    """
    d = dict(raw) if isinstance(raw, dict) else {}

    framing = d.get("framing_status")
    if framing not in FRAMING_STATUSES:
        framing = FRAMING_UNKNOWN
    calib = d.get("calibration_status")
    if calib not in CALIBRATION_STATUSES:
        calib = CALIB_UNAVAILABLE

    px = d.get("far_baseline_clearance_px_720")
    try:
        px = None if px is None else float(px)
    except (TypeError, ValueError):
        px = None

    reasons = d.get("reasons")
    reasons = [str(r) for r in reasons] if isinstance(reasons, (list, tuple)) else []
    if framing == FRAMING_UNKNOWN and not reasons:
        reasons = [UNKNOWN_SUMMARY]

    answer = d.get("far_baseline_user_answer")
    if answer not in (True, False):
        answer = None

    source = d.get("framing_source")
    if source not in ("clearance_geometry", "user_answer", "none"):
        source = "none"

    # `metrics_eligible` is RE-DERIVED, never trusted from the file. A stale or
    # hand-edited file must not be able to assert that its numbers are verified
    # when its own two axes say otherwise — that is the one field where believing
    # the input would let a wrong claim outlive the evidence for it.
    eligible = (framing == FRAMING_CLEAR and calib == CALIB_USER_CONFIRMED)

    return {"framing_status": framing,
            "far_baseline_clearance_px_720": px,
            "calibration_status": calib,
            "metrics_eligible": eligible,
            "reasons": reasons,
            "framing_source": source,
            "far_baseline_user_answer": answer,
            "notice": notice_for(framing)}


def summary_line(state: dict[str, Any]) -> str:
    """One line for a CLI or a status chip, from a normalized state dict."""
    s = normalize(state)
    if s["framing_status"] == FRAMING_CLEAR:
        return ("Framing clear" if s["metrics_eligible"]
                else "Framing clear - court corners not confirmed")
    if s["framing_status"] == FRAMING_LIMITED:
        return "Limited court accuracy"
    if s["framing_status"] == FRAMING_OVERLAP:
        return "Limited court accuracy - net hides the far baseline"
    return "Setup quality not recorded"
