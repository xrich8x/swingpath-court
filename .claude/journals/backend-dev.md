# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

**SCOPE: the court feature only (founder, 2026-09-17).** Earlier non-court history lives in the main repository (`xrich8x/swingpath`).

---

## TASK

**DONE and committed** (f3bddd6, branch `camera3d-pnp-paintfit`, NOT pushed). G8: make the far
lines checkable (Part A), pin the encoder (Part B), make the lock honest (Part C).
Pre-registration committed FIRST at 46e5fe7.

## STATE

Complete. 3 of 4 Part-A bars PASS, bar 4 (non-degradation on G7's scene) FAILS -> the far-line
instrument ships MEASURED BUT OFF (`camera3d.FAR_LINES_DEFAULT = False`). Part B PASSES with its
null control failing as required. Part C ships unconditionally. Suite 394 -> 414 pass, 10 skip,
same 2 pre-existing failures. Memory updated with 4 new entries.

NEXT IF RESUMED: nothing outstanding on this task. The open follow-up, which needs its OWN
pre-registration, is a CONFUSER GUARD for the far-line instrument (reject a ridge whose amplitude
is implausible for 5 cm of paint, or exclude the net's image band via `net_tape_clearance`).

## LOG
- CARRIED FORWARD: `python` is a broken Store shim -> use the CPU venv at
  "E:\Claude Outputs\Cowork Tasks\Swing Visionackend\.venv\Scripts\python.exe".
- CARRIED FORWARD: grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: long markdown via bash heredoc FAILS -> Write tool, then `cat >>`.
- CARRIED FORWARD: a bash heredoc running python ALSO fails when the next `&&` command holds
  quotes; write the patch script to the scratchpad and run it instead.
- CARRIED FORWARD: `sed -i` fails cross-device in the scratchpad ("Invalid cross-device link").
- CARRIED FORWARD: any script calling `court_fit_cp1.run_arm` needs an `if __name__` guard
  (Windows spawn) or the pool dies with BrokenProcessPool.
- CARRIED FORWARD: tools/ is at the REPO ROOT, not under backend/.
- CARRIED FORWARD: smoke-test at small n before any long run.
- CARRIED FORWARD: the `researcher` agent was DELETED by the founder 2026-09-18.
- G7 ANSWER (committed earlier): paint_check.ok catches 33/33 wrong cameras at 1/365; the fit's
  own cost is INVERTED (AUC 0.216).
- G8 ANSWER (f3bddd6): far lines observable (z 6.8-9.5, offset <0.05 px) via along-line
  stacking; held-out catch 0.9167 at 0.0000 incremental false flags; both documented knock
  frames caught (62.27 / 49.11 cm, locked-but-wrong 2 -> 0 on a paired A/B); BAR 4 FAILS
  369/369 on CP1's scene, cause isolated to NET TAPE clutter (5 px, 110 DN) not the lens
  (0.02 px). far_min_z INERT 3-8. Cost 3.36 -> 9.57 ms/frame. The founder's PYRAMID arm BEAT
  my stacked profile (1.000 vs 0.917) - prediction A3 wrong; never run against bar 4.
- Full numbers live in docs/evidence/court-camera3d.md G8 and in agent-memory; do not re-derive.
