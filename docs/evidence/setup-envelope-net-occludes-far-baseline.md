# Below ~2.2 m the net TAPE covers the far baseline — why five verification gates failed

> Evidence for the `setup-envelope-net-occludes-far-baseline` row in [../STATE.md](../STATE.md).
> Measured 2026-09-05 (lead), prompted by the founder's reframing: the user is holding the
> phone and can move, so **require** a framing rather than verify an arbitrary one.

## The question everyone had been asking was the wrong one

Five autonomous gates have now failed to tell a correct court from a wrong one — coverage and
centrality, the camera-height screen, the net-anchor `band_ratio`/`dy` bars, the net-post
detector, and fitted hfov. Every one of them tried to **verify** a calibration after the fact.

The error they all miss is the same one: **clicking the NET as if it were the far baseline**,
which compresses the court onto its near half. That is what `yt_match40` was, twice.

## The mechanism, and it is geometric rather than perceptual

A tennis net is **0.914 m tall at the centre**. At a low mount that height projects to *more
image rows than the entire far half of the court occupies*. So the net's white tape rises
**above** the far baseline in the image, and the two stop being separable — not "hard to tell
apart", **overlapping**.

Pinhole on the ground plane, camera 3 m behind the near baseline, hfov 80°, 720p:

| mount | net tape row | far baseline row | verdict |
|---|---|---|---|
| 1.40 m | 24.9 | 39.9 | **tape ABOVE the far baseline** |
| 1.64 m | 37.2 | 46.7 | **tape ABOVE the far baseline** |
| 2.00 m | 55.6 | 57.0 | **tape ABOVE the far baseline** |
| 2.50 m | 81.3 | 71.2 | far baseline clear by 10 px |
| 3.00 m | 106.9 | 85.5 | far baseline clear by 21 px |
| 4.00 m | 158.1 | 114.0 | far baseline clear by 44 px |

**The crossover is ~2.0–2.2 m and it barely moves.** Swept over standoff (2–5 m back), lens
(65–100° hfov) and resolution (720p / 1080p), the height at which the far baseline first clears
the tape at all is **1.99–2.22 m**; for a comfortable 10 px of clearance it is **2.19–2.98 m**.
It is stable because it is set by the **net's physical height against the far half's depth** —
a property of the court, not of the camera.

## Every clip that was mis-clicked this way sits below it

| clip | mount | |
|---|---|---|
| `yt_match40` | 1.64 m | mis-clicked exactly this way, twice |
| `am_hard_utr` | 1.74 m | one of the two "unsettled" sheets |
| `demo30` | 1.38 m | |
| `flexi_joy_p01` | 1.36 m | |

**So the two clips nobody could settle are not a labelling failure or a tooling failure. The
information is not in the image.** No gate, no detector and no human eye can separate a net
from a far baseline that overlaps it — which is exactly the pattern of five failed gates and
three of the lead's own wrong frame-reads.

## What this changes

**Stop trying to verify an arbitrary calibration; require a setup where the ambiguity cannot
occur.** That is already this project's instinct — `framing_report` and `run.py check` exist,
and `calibration.py`'s own comments say to control the input rather than solve the general
problem — but the height requirement had never been derived, only guessed at as
`min_elevation = 0.28` on a far/near width ratio.

**The requirement is reachable, and only just.** The repo's own stated prior is a fence clamp at
**~2.5 m** and a standing tripod at **~1.5 m**:

- **A fence clamp clears it.** 2.5 m gives 10 px of separation at 3 m back.
- **A standing tripod does not.** At 1.5 m the net tape sits above the far baseline, and no
  amount of careful clicking fixes that.

That is a **product constraint you can actually ask a user for**: *clamp the phone to the fence
rather than standing a tripod on the ground.* One sentence of setup guidance, and it converts an
unsolvable verification problem into a solvable framing one.

## What the app can show live, which is the founder's actual ask

The user is holding the phone and moving, so the check can run **continuously during setup**
rather than once afterwards. The quantity to display is the one derived above: **is the far
baseline visibly clear of the net tape?** It needs no calibration to evaluate — it is a question
about two lines in the current preview frame, and it is exactly the condition that decides
whether a correct calibration is even possible from where the user is standing.

That is a different and much easier problem than any of the five gates, because it is asked
**before** a homography exists rather than after.

## Limits, stated

- Ideal pinhole, flat court, no lens distortion, and it assumes the far baseline is in frame at
  all. A real 0.5x ultrawide has distortion this ignores.
- The 0.914 m is the net at the **centre**; it rises to 1.07 m at the posts, so the occlusion is
  slightly worse toward the sides than this centre-line calculation shows.
- It says when the two lines **overlap**, not when a human or a detector actually confuses them.
  The practical margin is wider than the geometric one.
- **It does not retro-justify any past number.** Clips below the threshold are not thereby proven
  miscalibrated — `am_hard_utr`'s ground line still matches its net base exactly. What follows is
  that they cannot be *confirmed* from a still frame, which is a weaker and different claim.
