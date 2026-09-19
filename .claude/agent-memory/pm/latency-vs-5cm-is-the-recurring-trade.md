---
name: latency-vs-5cm-is-the-recurring-trade
description: The cheap court path is the WARM/stateful one (0.020 s) and the cold one is 9.6 s; per-frame statelessness is measured at p90 9-11 cm, so latency proposals keep arriving as precision cuts in disguise
metadata:
  type: project
---

**The court's latency problem and its precision problem are the same problem, and the trade keeps
arriving disguised as an engineering optimisation.**

Measured at 1080p on desktop CPU (2026-09-17/18 session): **full cold paint fit 9.6 s, warm tracker step
0.020 s, `paint_check` 0.003 s.** The 500x gap between cold and warm is entirely "does it use the
previous frame".

**Why this matters for scope:** the founder's 2026-09-18 mandate prohibits temporal state, and G3
(`docs/evidence/court-camera3d.md`) measured what stateless costs — single-frame snaps give about **5 cm
median, p90 9.2–10.9 cm** under steady sway on good setups, i.e. above the 5 cm target and touching the
10 cm kill. Temporal averaging is the known route to the last factor of two. So a stateless mandate is a
precision decision, not only a performance one.

**How to apply:**
- Treat "make it fast" proposals as precision proposals until proven otherwise, and ask which line's p90
  pays. The far baseline's entire margin is **~1.4 cm** and the codec already spends **2.65 cm**
  (`docs/evidence/court-fit-cp1.md` qa audit) — so a fit that terminates on a downsampled pyramid level
  will not hold 5 cm.
- Never approve a hardware/language port (Metal, Core ML, C++) before a **desktop, same-seed experiment**
  shows the cheap *algorithm* keeps the per-line p90. A port cannot rescue an algorithm that lost
  precision.
- The worst outcome is not slow and it is not imprecise — it is a **confident wrong lock**. G3 measured a
  tracker reporting `tracking` while 7–10 m out for 50 frames, because its drift test compared its pose
  against its own flowed points. Any gate that certifies a court must be independent of the thing it
  certifies.

Related: [[seed-vs-answer-is-the-court-cut-line]], [[cheap-tests-that-close-a-line]].
