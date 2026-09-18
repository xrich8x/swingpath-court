# SPEC.md — the court feature (automatic, live 3D court mapping)

**Scope reduced to the court feature by the founder, 2026-09-17.** The full 2026-09-11 spec — ball
calls, landing accuracy, bounce detection, trajectory physics, occlusion, latency, pose, edge cases
for the ball — is preserved verbatim in
`swingpath:docs/archive/2026-09-17-pre-court-only/docs/SPEC.md`. **It is archived, not in force.**

Bars below that came from the 2026-09-11 spec are pre-registered under hard rule 2 and do not move
to fit a result. The founder alone changes them. **Nothing here has been met yet;** state lives in
`docs/STATE.md`.

---

## 1. Automatic, live 3D court mapping

### Founder rulings, verbatim — these govern everything below

**2026-09-17 — the court is found AUTOMATICALLY.** "dont use finger level accuracy - I keep saying
that it must be the machine learning the 3d space and determining the far and close lines and
assuming where the end points are if they are not visible similar to swing vision"

- Court setup must not depend on the precision of a human tap.
- The system learns the court's 3D layout, locates the near and far lines itself, and infers end
  points that are out of view from the regulation dimensions.

**2026-09-17 — court tracking CONTINUES; the app does not stop.** "must continue, its essentially live
court tracking so the app should know that the court is still there but just shaped differently
because the phone moved"

- When the phone moves, the court keeps being tracked and re-fitted. The app never refuses and never
  asks the user to re-tap.

**2026-09-18 — the court is FOUND IN EVERY FRAME; state is BOUNDED.** The founder first ruled that
tracking "shouldnt snap but continuously detect the court", choosing full per-frame detection with no
dependence on the previous frame; shown the measurements (stateless cold path 9.6 s/frame; best
measured stateless per-frame precision p90 9.2–10.9 cm, above the 5 cm target), they settled on
**bounded state**: *"the court is found in the image every frame, but the camera may be refined
across frames."*

- A saved court is **never propagated**, and there is **no snap**: every frame measures the court in
  that image.
- The camera **may** be refined across frames; temporal averaging is allowed and is the known route
  under 5 cm.
- An **independent on-paint check runs every frame**, so a wrong court can never be reported as good.
- The accuracy floor is unchanged (§3): every line p90 ≤ 5 cm, 10 cm kills.
- Recovery after a large change may use the automatic court finder. It may **not** use the specific
  search branches recorded dead in `docs/court/CLOSED.md` (rule 3).

**2026-09-11 (capability 1, founder brief).** "map the full court, including lines the camera cannot
see, from visible markers plus the universal regulation dimensions. Known geometry substitutes for
sight."

### Original §1 bullets (2026-09-11), kept as written except for one removed ball-call clause

Read through the rulings above: "recalibration" means a re-fit of the tracked court, and nothing here
halts the app. **The numbers (15 px, 10 s, 6/8) were set for a different mechanism and are
unmeasured for this one.** 15 px is ~5 m at the far baseline at 1080p / 3 m, and
that a sub-5 cm court needs a re-fit tolerance of ~0.1 px on far lines. The founder resets these
once a measurement exists.

- **Drift check:** every frame, track 4–8 court line-intersection points by optical flow. Trigger a
  full recalibration if mean reprojection error on those tracked points exceeds **15 px sustained
  for 3 consecutive frames** — single-frame spikes are noise, not camera movement.
- **Forced fallback recalibration:** full court re-solve every **10 s** (600 frames @60 fps)
  regardless of the drift signal, as a backstop.
- **During recalibration:** freeze the last-known court model until the new model passes the
  **8-frame vote (≥6/8)**. *(The original also held all ball calls here; ball calls are archived.)*

## 2. What the court model must output

- **Every painted line, doubles alley included — required, not optional** (2026-09-11, §10).
- **Lines out of view are inferred from the regulation dimensions** (capability 1).
- **A 3D court with a solved camera**, not only a flat image-to-court map.

## 3. Court accuracy — a WORKING target, not a founder-locked bar

**The founder has not set a number for the court model on its own.** The 2026-09-11 spec's 10 cm
target applied to landing calls, and that part is archived.

The team's pre-registered **working target**, used by the C1 and CP1 tests, derives from that budget:

- **PASS:** every line's perpendicular placement error ≤ **5 cm** at p90.
- **KILL:** any line above **10 cm** at p90.

It is a measurement convention, not a spec bar. Label it that way whenever it is quoted.

## 4. Capture conditions the court must work under (2026-09-11 §2)

- **Resolution: 1080p minimum.**
- **Mount:** fence-mount or tripod. **Handheld is out of scope** — its jitter needs separate tuning of
  §1's drift handling.
- *The 60 fps floor in the original §2 was a bounce-detection requirement; it is archived with the
  ball spec.*

## 5. Surfaces (2026-09-11 §7 and §10)

- **The court must work on hard, clay and indoor shell courts.** A court result that only holds on
  hard courts is not a passing result.
- **Indoor shell — founder ruling 2026-09-17 ("yes"):** the old shell blocker does not bar this
  feature.
  - That blocker was the automatic court SEARCH failing on shell: recall 8/20 = 40%, the search never
    once producing a correct court on 12 of 20 clips, with roof trusses and lights drowning the lines.
  - **That failure is now a known hard case the automatic finder must handle,** not a reason to skip
    shell.
  - Ten shell calibrations exist for testing.

## 6. What is archived (not in force)

Ball calls and landing accuracy (§3), bounce detection (§4), trajectory physics (§5), prediction
through occlusion (§6), the ball validation bars (§7), latency (§8), skeletal analysis (§9), and the
ball edge cases (§10: net cord, ball leaving frame, multiple balls). All are preserved in the archive
copy.
