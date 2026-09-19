---
name: undetected-is-not-failed
description: Separate DETECTED from HIT in any acceptance check; a blank measurement cannot tell a wrong model from an unobservable one, and calling it a failure is the same dishonesty reversed
metadata:
  type: project
---

**Any check that asks "is the model where the image says" must return THREE outcomes, not
two: verified, contradicted, and NOT OBSERVABLE.** In G8 (2026-09-19) the far-line check
returns `detected` (a ridge exists anywhere in the search window) separately from `hit`
(the ridge is within tolerance of the prediction). A profile with no ridge at all goes back
to `unchecked`, never to failed.

**Why:** the first version conflated them and immediately produced a false accusation — at
1280x720 the far baseline is genuinely below the noise, so every correct camera was reported
as a failed line. That is the same dishonesty the whole task existed to remove, pointed the
other way. The three-way result also made the 720p unit tests pass again without weakening
anything, because "I cannot see it" is the truthful answer there.

**How to apply:** carry the third state all the way to the user-visible claim, not just
inside the function. `PaintCheck.scope` / `TrackStep.lock_scope` / `setup.camera.lock_claim`
name WHICH lines were checked, and the claim sentence is RE-DERIVED on every read so a
hand-edited file cannot out-claim its scope. The corollary for search windows: if the window
is narrower than the errors you must catch, a large error reads as "not observable" and
escapes — G8's reach had to go from 3.0 to 8.0 px@720 because a 1.6 m far-baseline error fell
outside the window and was silently not flagged. Related: [[the-net-tape-owns-the-far-lines]],
[[null-controls-and-pre-registered-populations]].
