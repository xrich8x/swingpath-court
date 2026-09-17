# Decisions — the court feature

**Scope reduced to the court feature by the founder, 2026-09-17.** Every earlier entry — ball,
bounce, line calls, occlusion, capture visit, spec contradictions for the ball path, SwingVision's
ball levers — is preserved in `swingpath:docs/archive/2026-09-17-pre-court-only/docs/DECISIONS_PENDING.md`.
**Archived, not open.**

**How this file works:** batch founder asks into ONE update. Do not interrupt for them one at a time.
Each open entry says what is blocked, what it costs to unblock, and what is being done meanwhile.

---

## RULINGS ON RECORD (founder, 2026-09-17) — binding, do not reopen

1. **Court work only.** "Continue - remember only court related things." And: "Clear out ALL OTHER
   FEATURES aside from the court - save the information that has already been doen but all
   instruictioins aside from this court feature needs to be wiped from MD files so we dont randomly
   work on it."
2. **The court is found AUTOMATICALLY.** "dont use finger level accuracy - I keep saying that it must
   be the machine learning the 3d space and determining the far and close lines and assuming where
   the end points are if they are not visible similar to swing vision".
   - This settles the 2026-09-09 open item, "a court model trained on AMATEUR low-mount footage, on a
     leak-clean split — founder call".
   - It overrides the 2026-09-05 conclusion that manual setup is the product answer.
3. **Live court tracking continues when the phone moves.** "must continue, its essentially live court
   tracking so the app should know that the court is still there but just shaped differently because
   the phone moved". Re-fit, never refuse, never ask for a re-tap.
4. **Indoor shell courts are in scope** ("yes"). The old shell blocker (a SEARCH failure) does not bar
   the feature; it is a hard case the automatic finder must handle.
5. **The 2026-09-06 court-gold edits (commit `2e49f38`) were the founder's.** They stand; no re-score.
6. **No court visit is possible yet** ("can not do yet"). Long far-end tape strips are approved in
   principle but cannot be done in person. No metric real-court truth is available for now.

---

## OPEN — waiting on the founder (court only)

### A. The drift numbers in SPEC §1 (15 px, 10 s, 6/8) — NOT ready to decide yet

- **The issue:** these were set for a different mechanism. Researcher found 15 px is ~5 m at the far
  baseline at 1080p / 3 m; a court good to 5 cm needs a re-fit tolerance of ~0.1 px on far lines. The
  phone's motion sensor cannot see drift that small, so researcher recommends both an IMU bump
  trigger and a periodic image re-fit.
- **What unblocks it:** CP1 (whole-court fit precision), then a tracking test under simulated phone
  movement. Bring the founder a measured number, not an estimate.
- **Meanwhile:** CP1 is running.

### B. A blind click set for real-footage court checks (lower priority)

- **The issue:** the court gold's non-corner keypoints were computed from four clicks, so real footage
  has no independent check of line placement. A real check needs the founder to click T-junctions and
  service-line junctions directly, with no overlay, on ~20 frames. That needs a new tool mode and a
  pre-registered bar first; it is not built.
- **Why it waits:** human clicks (~17 px at 1080p) are far too coarse to settle sub-pixel precision.
  They can only catch gross real-world failures such as lens distortion or non-regulation courts.
- **Meanwhile:** nothing is asked of the founder.
