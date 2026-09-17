# Candidate proposal recall: does the court search EVER produce the right answer?

**qa, 2026-09-09. Court only. Measurement, not a build.**

## HEADLINE FOR backend-dev — READ THIS FIRST (posted before the write-up was finished)

**Proposal recall = 8 / 20 gold clips = 40%.** My **pre-registered** bar (written into
`.claude/journals/qa.md` before the audit was run) was:

- voting binds if recall >= 0.80
- **search binds if recall <= 0.60**
- indeterminate in between

**40% <= 60%: SEARCH BINDS.** On 12 of 20 gold clips the shipped per-frame court search
never once, across 8 sampled frames, produces a court within the accept tolerance
(`WRONG_PX_640 = 20.0 px @640`) of the human clicks. No downstream gate, score, vote or
agreement change can recover those 12 — there is nothing there to recover.

**On shell specifically: 1 of 5 shell recordings (2 of 10 shell clips).** That is exactly
on my pre-registered shell line (`<= 1/5` = search binds), so it is a **borderline**
search-binds, not a comfortable one — I am calling it borderline rather than rounding it up.
Only `flexi_franz` (2.50 m mount) ever reaches truth. `mpc_mixed_p02`, `mpc_mixed_p08` and
`mpc_tuesday_p07` produce **no lock at all in any of 8 frames** — the search returns nothing.

**So the external document's DIAGNOSIS is supported on this measurement**, most strongly
on shell. One load-bearing qualification before you build on it:

- This instrument measures the recall of the **post-conjunction per-frame winner**
  (`courtfit.auto_fit_frame`), which is a **lower bound** on raw proposal-stage recall.
  A candidate could be generated and then killed by the per-frame accept rule; that
  would still count as 0 here.

**The complementary half is already settled and it points the same way.** The scoring
criteria are *not* the bottleneck: the existing neighbourhood sweep shows that a court a
median **4.9 px** from the human clicks clears the accept gate on **19 of 20** references
(`data/output/court_scoring_diagnosis.md` §10; only `UHf0LeMU2pg` fails). This run also
emits a `truth_would_pass = 9/20`, and **that number must not be quoted** — it scores the
*exact* clicks, which is the identical artifact that got `0.18–0.31` withdrawn. Full
explanation in §4. Corrected reading: **the search binds; the criteria do not.**

If you are reordering CNN-global -> classical-local, the number that justifies the reorder
is **8/20 overall and 1/5 shell recordings**. Nothing here says a CNN will reach them —
that is the next measurement, and `auto_fit_frame(..., proposer="courtnet")` is already
wired, so it is one flag.

---

## What was measured, and against what

Instrument: `eval/candidate_audit.py` (already in the repo, written 2026-08-24). Extended
zero lines; run as shipped: `candidate_audit.py --k 8 --json ...`.

**Correction to the file's own docstring, which says UNRUN: it is not.** Session O ran it
on the 10 shell clips on 2026-08-24 — that run is `data/output/court_scoring_diagnosis.md`
§10 and `docs/evidence/indoor-shell-courts.md`. **This run is the first over the full
20-clip reference set**, and the first that anyone has compared against the earlier shell
numbers. The stale docstring is a finding for whoever owns the file, not something I fixed.

Population: `eval/run_refs.references()` — 20 clips carrying a **human-placed** `_exact:true`
calibration in `data/<clip>_pts.json`. `data/eala_pts_auto.json` is excluded by name and by
rule (self-grading). Every error below is the mean distance between the four doubles
landmarks as **projected** by the human homography and by a fit's homography, rescaled to
640 px width — the identical definition `run_refs.score` uses, so these numbers and the
gate's numbers mean the same thing.

Recall definition: a clip **reaches truth** if **at least one** of 8 sampled frames yields a
per-frame lock within **20.0 px @640**. Whether the vote accepts it is deliberately ignored —
that separation is the whole point of the exercise.

Mount heights are the `_audit.camera_height_m` stamps already in each `_pts.json`
(`validate_new_clip.py --stamp`); surfaces are the `data/incoming/<surface>/` folder.

## 1. Per clip: best-candidate error, not just a boolean

`errs` is every per-frame lock's error, sorted, so a near miss is visible as a near miss.

| clip | surface | mount m | locks/8 | good/8 | **best err px@640** | all per-frame lock errs |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| sAjkpeRq4P4 | Clay | 3.33 | 8 | 6 | **2.3** | 2.3 2.8 2.9 2.9 3.1 3.9 58.2 113.2 |
| CYqapSq5llo | Clay | 1.98 | 8 | 5 | **5.2** | 5.2 8.3 12.1 19.2 19.6 33.9 48.0 55.2 |
| A7vXlWIlyrI | Hard | 1.69 | 4 | 1 | **5.3** | 5.3 22.9 24.7 51.4 |
| flexi_franz_p07 | Shell | 2.51 | 3 | 2 | **6.6** | 6.6 9.7 28.2 |
| e8T34KoJzOw_s2 | Hard | 1.76 | 8 | 3 | **6.7** | 6.7 12.3 19.2 22.8 28.5 28.8 32.9 39.5 |
| am_hard_utr | Hard | 1.74 | 8 | 8 | **7.5** | 7.5 12.3 12.7 13.7 15.2 15.2 15.3 20.0 |
| flexi_franz_p01 | Shell | 2.50 | 3 | 3 | **8.8** | 8.8 12.3 19.6 |
| uR5q2cSM6AY | Hard | 3.32 | 8 | 1 | **18.7** | 18.7 20.4 20.8 27.4 28.5 30.9 35.1 36.0 |
| --- reached above / never reached below (20.0 px line) --- | | | | | | |
| HoHxFSX_gLk_s2 | Hard | 1.59 | 8 | 0 | 23.1 | 23.1 24.0 25.8 32.1 32.2 32.6 36.3 66.3 |
| hillsborough_p08 | Shell | 1.63 | 3 | 0 | 27.6 | 27.6 48.5 52.3 |
| UHf0LeMU2pg | Hard | 3.35 | 7 | 0 | 35.7 | 35.7 46.1 48.9 51.5 58.9 63.0 76.3 |
| hillsborough_p02 | Shell | 1.64 | 3 | 0 | 37.2 | 37.2 43.4 61.7 |
| flexi_joy_p07 | Shell | 1.36 | 5 | 0 | 40.8 | 40.8 46.0 50.9 67.1 73.8 |
| flexi_joy_p01 | Shell | 1.36 | 2 | 0 | 40.8 | 40.8 42.2 |
| tc8CGFxyRE8 | Hard | 2.00 | 7 | 0 | 41.8 | 41.8 46.9 50.5 66.9 68.5 70.5 90.9 |
| HoHxFSX_gLk_s1 | Hard | 1.71 | 3 | 0 | 60.5 | 60.5 72.7 91.4 |
| mpc_tuesday_p01 | Shell | 2.79 | 1 | 0 | 111.4 | 111.4 |
| mpc_mixed_p02 | Shell | 1.64 | 0 | 0 | **no lock at all** | (none) |
| mpc_mixed_p08 | Shell | 1.63 | 0 | 0 | **no lock at all** | (none) |
| mpc_tuesday_p07 | Shell | 2.81 | 0 | 0 | **no lock at all** | (none) |

**Three qualitatively different failures, which "refused" hides:**

- **Near miss (2 clips):** `HoHxFSX_gLk_s2` 23.1 px, `hillsborough_p08` 27.6 px. Both sit in
  the 20–30 px band. These are the only clips where a tolerance argument could change the
  verdict, and I am not making one — the 20 px line is pre-registered and does not move.
- **Wrong court (15 clips):** best lock 35–111 px. Not a fitting error; a different court.
- **Nothing produced (3 clips, all shell):** zero locks in 8 frames.

**Tolerance sensitivity (reported, not used to set the verdict):** recall is 8/20 at 20 px,
would be 8/20 at 22 px, 10/20 at 30 px, and still 10/20 at 35 px. The SEARCH-BINDS verdict
(<= 0.60) holds across the entire 20–35 px range, so it does not depend on where in the
empty band the line sits.

## 2. Split by surface

| surface | clips | recall (clips) | recall (recordings) | best-err median of the misses |
| --- | ---: | ---: | ---: | ---: |
| Clay | 2 | **2/2 = 100%** | 2/2 | — |
| Hardcourt | 8 | **4/8 = 50%** | 3/7 (`HoHxFSX_gLk_s1/s2` share a source) | 38.8 px |
| **Shell (indoor)** | 10 | **2/10 = 20%** | **1/5 = 20%** | 40.8 px |

Shell is reported by **recording** as well as by clip because the 10 shell clips are 2 points
each from 5 recordings (`flexi_franz`, `flexi_joy`, `hillsborough`, `mpc_mixed`,
`mpc_tuesday`) — these are the "0 of 5" shell set, and the two clips of a recording are not
independent evidence. **1 of 5 shell recordings ever produces a correct candidate.**

This is consistent with the standing 0/5 shell acceptance and it **locates** the failure:
shell does not fail at the vote, it fails before there is anything to vote on. Three of the
ten shell clips return **no lock whatsoever**, which no accept-side change can touch.

Against the document's specific claim (clutter drowning the 8 court lines): this measurement
is **consistent** with it but does **not** establish it — I did not render the masks or count
mask pixels this run, so "the building drowns the lines" remains the prior explanation
carried in from earlier work (395k–1,257k mask px), not something this run confirmed.

### Shell has been measured on this instrument before — and it has moved by one clip

`data/output/court_scoring_diagnosis.md` §10, 2026-08-24, same script, same 10 shell clips:

| shell split | Session O, 2026-08-24 | this run, 2026-09-09 |
| --- | ---: | ---: |
| truth inside the candidate set | **3 / 10** | **2 / 10** |
| locks exist, none is true | 4 / 10 | 5 / 10 |
| no lock at all | 3 / 10 | 3 / 10 |

Same direction, **one clip worse**. I cannot name the clip: the archived summary keeps only
the aggregate, no per-clip table. Two secondary signs that this is real movement rather than
a reporting difference — Session O reports the within-frame margin as positive on all four
never-reached clips (+0.041, +0.051, +0.163, +0.355), whereas mine are +0.166, +0.107,
+0.251, **−0.009, −0.023**: two have flipped sign, and the +0.355 is now +0.251.

**A specific thing worth someone's eye, offered as a lead and not as a finding:** commit
`4a33635` scaled the court refiner's reach from `max_move_px = 55` to `55 * w / 640` and was
validated as "moves no number (gold 12/20 -> 12/20), an exact no-op on the gate"
(`docs/STATE.md:88`). **The shell clips are 3840x2160, so that factor is 6x there, and shell
is not in the gate pool** — a shell-only effect would have been invisible to the validation
that cleared it. I have not tested this; I am naming it because it is the one change since
2026-08-24 whose blast radius is resolution-dependent and whose control was resolution-blind.

### One of the five shell recordings is not usable as truth

Session O measured `mpc_tuesday`'s two independent human labels as disagreeing by **25.4 px**
— above the 20 px wrong-court line, i.e. its own ground truth is less self-consistent than
the amount separating a right court from a wrong one. On the **4 shell recordings whose truth
is trustworthy**, proposal recall is **1 / 4 recordings (2 / 8 clips = 25%)**. That is the
number I would quote; it does not change the verdict, and `mpc_tuesday` fails on both
countings anyway (111 px, and no lock at all on p07).

**The one shell recording that works is the exception worth looking at:** `flexi_franz`
reaches truth at 8.8 and 6.6 px, on a **2.50 m** mount — the highest shell mount that is not
`mpc_tuesday`. `mpc_tuesday` is higher still (2.79/2.81 m) and is the single worst clip in
the whole set (111 px, and no lock at all on p07), so height alone does not explain it.

## 3. Split by mount height — the pre-registered mechanism test, and it FAILS

The mechanism under test: below ~2.0–2.2 m the net tape physically overlaps the far
baseline (16 of 28 calibrations), so a correct candidate could be **unproposable in
principle** there. I pre-registered that this counts as an established, distinct mechanism
only if recall drops by **>= 40 percentage points** across the boundary with >= 3 clips in the
low group.

| mount band | clips | recall |
| --- | ---: | ---: |
| < 2.0 m | 12 | 4/12 = **33.3%** |
| >= 2.0 m | 8 | 4/8 = **50.0%** |

**Gap = 16.7 pp, against a pre-registered 40 pp bar. THE MECHANISM IS NOT ESTABLISHED.**
The bar was set before the numbers were seen and it stays where it is.

Finer bands, for completeness (small n, do not over-read):

| band | clips | recall |
| --- | ---: | ---: |
| 1.36–1.71 m | 8 | 2/8 = 25% |
| 1.74–2.00 m | 4 | 3/4 = 75% |
| 2.50–2.81 m | 4 | 2/4 = 50% |
| 3.32–3.35 m | 3 | 2/3 = 67% |

**Recall does not collapse at the 2.0–2.2 m boundary.** The best clip in the whole set
(`sAjkpeRq4P4`, 2.3 px) is at 3.33 m, but so is a total miss (`UHf0LeMU2pg`, 35.7 px at
3.35 m), and the second-best (`CYqapSq5llo`, 5.2 px) is at 1.98 m — below the boundary.
The two lowest mounts in the set (`flexi_joy`, 1.36 m) fail, but they are also shell, so
height and surface are **confounded**: 8 of the 12 sub-2.0 m clips are shell. With this
population you cannot separate the two, and I am not going to claim you can.

Plain reading: **surface separates the data; mount height does not.** The net-tape/far-
baseline mechanism is not refuted — it is simply not visible at this sample size and is
confounded with surface.

## 4. Which stage binds — plainly

**The SEARCH binds, on 12 of 20 clips (60%), and most severely on shell (4 of 5 recordings).**

But the audit also evaluates the shipped per-frame accept conjunction directly **on the
human court**, which answers the complementary question — if the search handed the accept
rule the right answer, would it take it?

> **the human court would be ACCEPTED on 9/20 clips.**
> blocking terms: `g>=.33` x11, `struct` x4, `verify` x4, `suffic` x3.
> **selects AGAINST truth** (the detector's own locks pass a term the truth fails) on
> **9 clips**: `A7vXlWIlyrI`, `am_hard_utr`, `CYqapSq5llo`, `e8T34KoJzOw_s2`,
> `hillsborough_p02`, `HoHxFSX_gLk_s1`, `HoHxFSX_gLk_s2`, `sAjkpeRq4P4`, `UHf0LeMU2pg`.

### DO NOT QUOTE THE 9/20 — I nearly drew the wrong conclusion from it, and here is why

My first draft of this section read "both stages are broken". **That was wrong and I am
retracting it in place rather than quietly deleting it**, because the way it was wrong is
instructive and has now caught two people.

`truth_would_pass` is computed on the **exact human clicks**, and is `False` if **any single
one of 8 frames** fails **any** one term. Both halves inflate the failure count:

- Scoring the exact clicks while the product gate allows 20 px is *precisely* the artifact
  that got `0.18–0.31` withdrawn from this repo. A court 5 px from the clicks routinely
  passes terms the clicks themselves fail.
- The shipped accept needs 6 of 8 agreeing frames, not 8 of 8 spotless ones.

**Proof from this very run that it is distorted:** on **5 of the 8 clips where a good lock
WAS produced** (`A7vXlWIlyrI`, `am_hard_utr`, `CYqapSq5llo`, `e8T34KoJzOw_s2`,
`sAjkpeRq4P4`) the audit marks the truth as "would not pass" — while a court *within 20 px
of that same truth*, in those same frames, demonstrably did pass. The metric contradicts
itself on a quarter of the corpus.

**The correct instrument already exists and was already run.** The neighbourhood sweep over
all 20 references (`data/output/court_scoring_diagnosis.md` §10): at a median **4.9 px** from
the clicks, the true court **clears the 0.33 accept gate on 19 of 20** clips and has a
positive margin on 19 of 20. Only `UHf0LeMU2pg` fails — and `UHf0LeMU2pg` is also one of my
never-reached clips (best lock 35.7 px), so it fails on both sides.

**Corrected verdict, and it is now unambiguous:**

> **The search binds. The criteria do not.** The scoring/accept side takes the right court on
> **19 of 20** clips when it is handed one at realistic precision. The search hands it one on
> **8 of 20**, and on **1 of 5 shell recordings**. There is no second bottleneck to split the
> blame with.

This also puts my number in **agreement** with Session O's independent conclusion ("the
scoring criteria are not the bottleneck on shell, or anywhere else — the search is"), which
is worth stating plainly: two runs three weeks apart, on the same instrument, reach the same
verdict, and mine extends it from 10 shell clips to all 20 references.

**The one part of the 9/20 output that survives** is `selects_against_truth` — the detector's
own locks passing, frame-for-frame, a term the truth trips (9 clips; `g>=.33` dominant at 11).
That is a within-frame comparison against locks in the same frames, so the exact-clicks
inflation applies to both sides of it equally. It is a real signal that `g>=.33` is
mis-ordering candidates, and it is consistent with Session O's finding that the accept gate's
coverage statistic "orders clips by line VISIBILITY, not correctness". It is a **ranking**
defect inside the search, not a reason to call the accept stage the bottleneck.

**Recommended follow-up for whoever owns `eval/candidate_audit.py`** (I did not edit it):
report `truth_pass_frames / n_frames` instead of a union-over-frames boolean, and score a
jittered court ~5 px off the clicks rather than the clicks themselves. Two lines of output,
and it stops the file emitting a headline number in the withdrawn-figure genre.

## 5. What this does and does not license

- **Licensed:** "the shipped classical search never generates a correct court on 60% of gold
  clips, and on 4 of 5 shell recordings" — measured, 8/20 and 1/5, robust to tolerance
  20–35 px.
- **Licensed:** "shell fails before the vote, not at it" — 3 of 10 shell clips produce no
  lock at all; none of the 10 produces a lock better than 27.6 px except `flexi_franz`.
- **NOT licensed:** "a CNN will fix it." Nothing here measures a CNN. This says the current
  proposer is the binding constraint on 12 clips; it says nothing about whether any
  replacement reaches them. That is a separate measurement on the same instrument
  (`auto_fit_frame(..., proposer="courtnet")` is already wired, so the A/B is one flag).
- **NOT licensed:** "clutter is why shell fails." Consistent with, not shown by, this run —
  no mask was rendered.
- **NOT licensed:** any mount-height claim. The pre-registered 40 pp bar was missed at
  16.7 pp, and height is confounded with surface in this population.
- **NOT licensed:** quoting this run's `truth_would_pass = 9/20` as an accept-rate. It is
  the withdrawn-figure artifact (§4). The accept-side number is **19/20** from the
  neighbourhood sweep.
- **NOT licensed:** pooling these 20 clips with the 20-clip `data/gold/*.court.labels.json`
  (`am_*`) pool. They are **different populations** with different filenames; do not merge.
- **NOT licensed:** treating the shell 3/10 -> 2/10 movement as a confirmed regression. It
  is a one-clip difference between two runs three weeks apart with no per-clip record kept
  from the first; it needs someone to re-run at `4a33635^` to become a finding.

### Decisions this run surfaces for the lead / founder (I am not taking them)

1. **Narrow `docs/STATE.md:196`** from "DIAGNOSIS: CONTRADICTED" to "contradicted outside
   shell; supported on shell (qa 1/5 recordings, Session O 3/10 clips)". researcher pre-
   stated this exact condition and it has fired. Not my row to edit.
2. **Is the shell 3/10 -> 2/10 drift worth a run?** One clip. The cheap test is
   `candidate_audit.py --clips <the 10 shell>` at `4a33635^` vs HEAD.
3. **`eval/candidate_audit.py` emits a headline number in a withdrawn genre** and its
   docstring says UNRUN when it has been run. Both are corrections to a file I may not edit.

## 6. Exchanges with the other two agents

**No exchange happened, and the reason is a tooling gap the lead should know about.** My
brief stated "Teams mode is ON — you have `SendMessage` and it works now." **`SendMessage`
is not present in my toolset** (Read / Write / Edit / Bash / Grep / Glob only). This is the
second consecutive run where a brief asserted I had it and I did not (recorded in
`.claude/agent-memory/qa/dispatch-collision-cleanplate-task.md` from 2026-09-06). I
therefore published the headline into the top of this file first, before finishing the
write-up, so that backend-dev has a readable channel.

**researcher's row and mine are NOT in conflict — its own narrowing condition is now met.**
`docs/STATE.md:196` records "DIAGNOSIS: CONTRADICTED ... the correct court is generated
7/10, reachable 31/38 ... recognised by the criteria 9/10 — then lost at the consensus
vote", which at first read looks opposite to my 8/20 and 1/5. Reading
`docs/evidence/external-research-reconciled.md` (read-only; I did not touch it) resolves it,
and researcher deserves credit for having pre-stated the condition rather than leaving it
implicit. Its §3.4 says, verbatim:

> "**One number would overturn this paragraph, and only one: proposal-stage recall split by
> surface.** The pooled 7/10 and 31/38 are across all surfaces. The document's claim is
> specifically about **shell** ... If shell proposal recall is near zero while pooled is 70%,
> the document is **right about shell** and my §3.2 verdict should be narrowed to
> 'contradicted outside shell'. **That is qa's live measurement and I could not obtain it.**"

**That condition fires.** Shell proposal recall is **1/5 recordings / 2/10 clips**, and
Session O independently measured 3/10 on the same clips three weeks ago. So researcher's
§3.2 verdict should narrow to **"contradicted outside shell; supported on shell"**.

Two units notes that must travel with any merge of the two documents:

- **`7/10` and my `8/20` are different populations, not a disagreement.** The 7/10 is the
  **10 original calibrated clips**, from `docs/evidence/court-detection-frames-that-each-
  find-the.md` (2026-08-24). My 20 are `run_refs.references()` — those 10 plus the 10 shell
  clips. 7/10 non-shell + 2/10 shell would be 9/20; I measure 8/20, i.e. one non-shell clip
  lower, which is the same order of drift as the shell 3/10 -> 2/10 above and is consistent
  with it being one effect rather than two.
- **researcher's "recognised by the criteria 9/10" is the good number; my `truth_would_pass`
  9/20 is not.** They are numerically similar and mean different things (§4). Do not let the
  coincidence of "9" merge them.

**No exchange of these points with researcher or backend-dev was possible** (no message
tool). They are written here and flagged for the lead.

## 7. Reproduce

```
backend/.venv/Scripts/python.exe eval/candidate_audit.py --k 8 --json out.json
```
~20 min wall (the 10 shell clips are 3840x2160). Deterministic; no seed involved.
Raw rows: 20 objects with `best_err`, `errs`, `n_good`, `truth_fails`,
`selects_against_truth` per clip.
