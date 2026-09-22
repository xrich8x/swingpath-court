# backend-dev memory

Index only. Content lives in the linked files. Restructured 2026-08-28 from a single
monolithic file; nothing was dropped.

- [Where authoritative detail lives](where-authoritative-detail-lives.md) — the repo docs to read before scoping or proposing anything
- [iOS architecture rules](ios-architecture-rules.md) — ANE pinning, fixed shapes, sequential decode, checkpointing; constraints not preferences
- [Calibration trap: check corners first](calibration-trap-check-corners-first.md) — a 0.9 px residual passed a calibration with no corner on any court line
- [Traps this project paid for](traps-this-project-paid-for.md) — unscaled constants, stale stamps, fps confusion, rates about the wrong subject, counts nobody rendered
- [Null controls and pre-registered populations](null-controls-and-pre-registered-populations.md) - a FAILING null control is what makes a failed gate clean; a population described two ways is two sets
- [Band ratio of medians is a weak instrument](band-ratio-of-medians-is-a-weak-instrument.md) — seed-unstable enough to flip a sign; use accept-precision vs base rate, and seed-sweep before quoting
- [Court fit ceiling is the LINES](court-fit-ceiling-is-the-lines.md) — all-lines least squares FAILS at 19.80 px; it out-fits the human homography, so the evidence floor is upstream of the fit
- [Net GROUND vs net TAPE](net-ground-vs-net-tape.md) — two rows, 0.914 m apart; confusing them condemned a CORRECT calibration, and band_ratio is a FAILED instrument
- [Net tape height is precision-limited](net-tape-height-is-precision-limited.md) — AGREES with the fitted heights; the 10% bar is ~3 px of tape row at 720p, so eyeball reads say nothing
- [Post loses on precision, not sensitivity](post-loses-on-precision-not-sensitivity.md) — net post FAILS 3/11 despite being 15% more sensitive per px; a confuser spanning both posts breaks the two-object cross-check
- [Net-tape clearance is the setup criterion](net-tape-clearance-is-the-setup-criterion.md) — px margin replaces the guessed 0.28; the width ratio is rho +0.189, camera height +0.937; 16/28 clips OVERLAP
- [Composite beats its members but fails the bar](composite-beats-its-members-but-fails-the-bar.md) — 57% held-out vs 80%, yet no solo matches it; coherence pairs save eala and exonerate the one real wrong calibration
- [Rows are detectable, widths are not](rows-are-detectable-widths-are-not.md) — near-baseline ROW 0.83 px@640 but WIDTH 12.4 and net width 44.6; the cross-ratio protects the far row, not the far corner
- [The rho gate is inert for oblique lines](rho-gate-is-inert-for-oblique-lines.md) — corr_attrib._match_line accepted sideline matches up to 316 px@640 off truth
- [Upstream CourtNet does not fire on amateur](upstream-courtnet-does-not-fire-on-amateur.md) — the CNN-global flip FAILED 12/20 -> 2/20; 2-3 of 14 keypoints, so no proposal at all
- [CourtNet weights substitute silently + two gold populations](courtnet-weights-silently-substitute.md) — courtnet_ft.pt overrides what you pass; "12/20 gold" and "2/20 references" are different sets
- [Audit instruments have failure modes](audit-instruments-have-failure-modes.md) — the corner sheet showed frame 0 while the eval scores 5%-95%; gallery placements make that a FALSE-ACCUSATION risk
- [References pool is STRICT-16, not 20](references-pool-is-strict-16.md) — founder ruling 2026-09-09; every `/20` against it is stale, and three different "20"s exist
- [Court gold provenance is UNATTRIBUTED](court-gold-provenance-is-unattributed.md) — `_exact` is a checkbox not a human marker; 9/20 refs placed by a self-grading agent session; blame values, not commits
- [Core ML export runs on LINUX](coreml-export-runs-on-linux.md) — 1x CI billing not macOS's 10x; the manylinux1 tag trap, and ultralytics' silent .mlmodel fallback
- [Sub-pixel renderer + boundary degeneracy](subpixel-renderer-and-boundary-degeneracy.md) — CP1: blur BEFORE binning; thin line on a colour step needs kappa (~1.3 cm per 5%)
- [Photometric lock signal SEPARATES](photometric-lock-signal-separates.md) — paint_check catches 33/33 wrong cameras at 1 in 365; the fit's OWN cost is INVERTED, AUC 0.216
- [Renderers cannot place sub-pixel paint](renderers-cannot-place-subpixel-paint.md) — fixed-grid samples miss by PHASE and binning-before-blur quantises POSITION; no `ss` fixes either
- [The net tape OWNS the far lines](the-net-tape-owns-the-far-lines.md) — clutter moved a far-line ridge 5 px where the lens moved it 0.02; 369/369 right cameras flagged
- [A second profile, never an edit](a-second-profile-never-an-edit.md) — determinism and fidelity fixes change the SCENE; flag them, default to the old behaviour, null-control must FAIL
- [Undetected is not failed](undetected-is-not-failed.md) — three outcomes, not two; and a search window narrower than the errors you must catch hides them as "unobservable"
- [Narrow window turns misses into unseen](narrow-window-turns-misses-into-unseen.md) — 3x-tol window + wing MAD: an off-tol ridge reads unseen and leaves the denominator; 49 cm locked
- [Tracker fails on the stale knock frame](tracker-fails-on-the-stale-knock-frame.md) — G9 KILL: 1.45 cm p90 but 5/6 knock frames locked 41-65 cm out; seeds 500-505 spent
