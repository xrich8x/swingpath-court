# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

**SCOPE: the court feature only (founder, 2026-09-17).** Earlier non-court history lives in the main repository (`xrich8x/swingpath`).

---

## TASK

G8 REMEDIATION after qa's 2026-09-19 audit (branch `camera3d-pnp-paintfit`, commit locally, do NOT
push). Seven steps: (1) fix Fault A - `tools/court_far_line_gate.py` calls `paint_check` without
`far_lines=True`; (2) re-run BAR 4 (and 1/2/3) at the PRE-REGISTERED reach `3 * far_tol` = 2.25 px
@720 instead of the shipped hard-coded 8.0; (3) re-decide BAR 4; (4) declare the deviation in the
evidence without rewriting it; (5) score the founder's pyramid arm against BAR 4; (6) close the
lock-scope forgery hole (scope vs `lock_unverified`) + test; (7) record qa's smaller corrections.

## STATE

RESUMED 2026-09-22 (founder Phase 1: PART 1 G8 re-decide at reach 2.25, then PART 2 G9 tracking gate
under --subpixel, pre-registered on fresh seeds). Suite on 572fd6d: 412 pass/10 skip/4 fail = the 2
pre-existing + 2 caused by WIP (test coupling in test_far_line_check; test_cost_separation asserted
far lines become checked on CP1 true cam - at 2.25 they go UNCHECKED, which is qa's prediction).
DECISION: BUILD ON 572fd6d (edits match the plan), fix the 2 tests.

OLD PLAN (still valid): Read journal, CLAUDE.md, STATE.md, G8 prereg+results, QA AUDIT 2026-09-19. Plan fixed:

- camera3d: add `FAR_REACH_MULT = 3.0`, `FAR_REACH_PX_720 = 2.25`; `far_line_stacks` default reach
  8.0 -> 2.25; `far_line_profile` reach defaults to `3 * far_tol` (registered coupling). 8.0 stays
  reachable explicitly so the published table reproduces.
- gate tool: add `far_lines=True` (Fault A) + `--reach-mode {fixed,registered}` (fixed = 8.0,
  reproduces published; registered = 3*tol per cell, pyramid too).
- BAR 4: `court_cost_separation.py --n 400 --seed 0` with a PAIRED third arm at the registered
  reach + a pyramid arm, all on the same image/camera.
- BAR 3: re-run tracking sim seeds 101/201 far-lines-ON at registered reach, compare to the
  committed OFF arm.

NEXT IF RESUMED: see LOG for the last completed step.

## LOG
- CARRIED FORWARD: `python` is a broken Store shim -> use the CPU venv at
  "E:\Claude Outputs\Cowork Tasks\Swing Vision\backend\.venv\Scripts\python.exe".
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
- G7 ANSWER: paint_check.ok catches 33/33 wrong cameras at 1/365; the fit's own cost is INVERTED.
- G8 ANSWER (f3bddd6): far lines observable; held-out catch 0.9167 at 0 false flags; BAR 4 FAILED
  369/369 on CP1 at reach 8.0. qa: that reach was NOT registered. Full numbers in the evidence file.
- 2026-09-22 RESUMED. Built on 572fd6d. Fixed 2 tests (reach coupling; CP1 true cam far lines
  UNCHECKED at 2.25). Pyramid guard in gate tool (window < 0.5 px/level -> skip level; none -> unseen).
  Sim stamp now records RESOLVED tracker cfg (was TrackConfig() defaults). setup_state: bare-string /
  odd lock_unverified counts as evidence; 5 forgery tests in test_far_line_check (19 tests now).
- FAULT A DONE: `--reach-mode fixed8` on 400-402 == published heldout artifact, 0/13,680 cells differ;
  0.75|5 = 0.9167/0.0000. File: data/output/court_far_line_gate/g8r/heldout_fixed8.json
- RUNNING: dev sweep registered reach -> g8r/dev_registered.json (for pyramid knobs + re-choice).
