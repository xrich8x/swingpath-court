# eval/frames — the drop-zone

Put court frames here to see how the detector behaves on them. Two layouts:

```
eval/frames/anything.jpg              one loose frame, graded on its own
eval/frames/manila_shell_1/*.jpg      a subdirectory = one clip, so its frames can VOTE
```

Prefer the subdirectory form. The shipped accept rule is a **≥6-of-8 frame
consensus**, so a single frame cannot reproduce what the pipeline actually does —
8 frames spread across a clip can. Frames from the *same fixed camera* on the
*same court*; the vote assumes the court does not move.

Run it:

```
backend/.venv/Scripts/python.exe eval/run_eval.py --drop
```

## What you get, and what you do not

**No ground truth lives here.** These frames have no human-clicked corners, so
`run_eval.py` can only report **lock / refuse** and write the overlay. It will
print `-` in the `corner_px` column and say so in the footer. Do not quote a
pixel accuracy number from anything in this directory — there isn't one to quote.

For a *measured* number the frames need corners clicked, which is what
`data/gold/*.court.labels.json` holds for the 20 clips in the gold set. If a
surface here turns out to matter, the way to make it measurable is to label it
with the Court page of `tools/gold_label_server.py` and let it join that set —
at which point it becomes TEST data and is **one-way**: never trained on, never
tuned against if it lands in the held-out split.

## What the overlays show

`eval/out/<clip>/f<frame>.png` is three panels side by side:

| panel | what it is | what it tells you |
|---|---|---|
| left | the frame + the fitted court (green) + human GT quad (blue, gold clips only) | is the court in the right place |
| middle | `line_ridge_mask` — the white-line channel | does the *default* mask see any paint |
| right | `_clay_mask` — the hue-agnostic channel | does the *retry* mask see paint the default missed |

The middle/right pair is the surface diagnosis. A clip that refuses with an empty
middle panel and a populated right one is a **colour-gate** failure (`sat < 90`
threw the paint away). One where both are populated but the fit still refuses is
an **acceptance-threshold** failure. Those are different bugs with different fixes,
and the panels are the only thing that separates them at a glance.

Useful surfaces to drop here, in the order they'd change the work:
clay and shell (faded, low-contrast, chroma-carried lines), courts with
pickleball or other multi-sport overlay lines, and any low-mount or
cut-off-corner framing that looks wrong in the app.
