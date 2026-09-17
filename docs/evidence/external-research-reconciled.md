# The founder's external research document, reconciled against what we measured

**researcher, 2026-09-09. COURT ONLY** — founder directive. The document's ball, bounce,
shot-classification, mobile-runtime and Ultralytics-AGPL sections are **parked** and appear
below only where they bear on a court decision.

---

## 0. Read this first: two limits on this run, stated before any verdict

**(a) The source document is not on disk and I could not open it.** `Glob` and `Grep` were
100% non-functional this run (T25 — every call returned "No files found", including `*` on
the repo root), so I could not enumerate the tree. I tried eight guessed paths
(`docs/EXTERNAL_RESEARCH.md`, `docs/external_research.md`, root `EXTERNAL_RESEARCH.md`,
`docs/research/external-research-2026-09-08.md`, `docs/research_notes.md`,
`docs/FOUNDER_RESEARCH.md`, `docs/research/`, `docs/evidence/external-research-reconciled.md`)
and all returned ENOENT. **This reconciliation is therefore against the lead's restatement of
the document's court claims** (`.claude/journals/lead.md`, NOW section, lines 136-164) plus the
eleven items itemised in my brief. Every claim I grade below is one of those; I graded nothing
I had to guess at.

**Consequence, and it is not cosmetic:** I can answer the document's **Q1 and Q2** because the
brief names them. **I cannot grade Q3, Q4 and Q5 — I have never seen them.** Anyone reading
this for "the five open questions now answer to" gets two of five. Handing me the file closes
that gap in one read.

**(b) I have no `SendMessage` tool.** The brief says teams mode is on and instructs me to ask
`qa` for the proposal-stage recall number. My actual tool list this run is
`Read / Write / Edit / WebSearch / WebFetch / Grep / Glob`. **There is no message tool, so I did
not get qa's number and I have not used one.** Where qa's number is decisive I say so and leave
the question open rather than substituting a guess. It is decisive in exactly one place
(§3.4) and I have pre-registered the test it gates (§6).

**What every number below was measured against, in one sentence each:** upstream's figures are
**self-reported on its own 25% validation split of the same 8,841-image YouTube broadcast
highlight pool it trained on**; ours are measured against **human-clicked court corners on
amateur phone footage**, TEST-split only, per `docs/STATE.md`.

---

## 1. Verdict table — every court item in the document

| # | Item as the document states it | Verdict | The measurement that settles it |
|---|---|---|---|
| 1 | Add a synthetic **court-centre 15th keypoint** to stabilise heatmap training | **ALREADY DONE — and more so than the document knows** | `backend/swingvision/_courtnet.py` docstring: "outputs 15 heatmaps (14 court keypoints + 1 court-centre used only for training convergence)"; `CourtNet.__init__(out_channels=15)`, `conv18 → 15`. It is not our addition — it is **upstream's own architecture**, confirmed first-hand on the repo README ("output tensor has 15 channels (14 from dataset and one additional point is center of tennis court)", included "for better convergence"). The document recommends adding a feature that is inherent in the checkpoint it recommends. |
| 2 | **Duty-cycle** court detection to every ~30 frames rather than per frame | **NOT APPLICABLE — we already exceed it by two orders of magnitude** | `docs/modules.md:130`: *"Court detection is one-time (calibration), not per-frame — already efficient."* We run it **once per video** over an 8-frame consensus vote (the 6/8 bar; see STATE's "Lowering the court consensus bar 6/8 -> 5/8"). One-in-30 would be a **91x increase** in court compute over what we do. This is not a saving, and it is not even a change in kind — it is a regression. |
| 3 | **Central claim, diagnostic half:** our shell failure is a *global search* failure (trusses, lights, mesh outnumbering the 8 court lines in Hough), and this unifies five prior rejections as one systematic error | **CONTRADICTED** | Decided in §3. Three of the five rejections it claims to unify are *positive evidence against it*: reachability (**31 of 38** clips, nearest seed already within refinement reach — a fired stopping rule), the widened seed grid (**reaches** the true far-width courts and **gets every one wrong**, 26 px and 78 px), and the consensus bar (the one 5-vote clip is wrong by **68.7 px**). The project's own summary: *"The criteria do recognise the correct court (9 of 10). The search does produce it (7 of 10). The frames that each found it do not agree with each other"* — 13 of 18 clips disagree principally about **WIDTH**. |
| 4 | **Central claim, prescriptive half:** run **CNN-global → classical-local** instead of our classical-global → CNN-fallback | **NOT DISPROVEN, and specifically NOT retired by the court closure — but its expected value is now low** | §3.3. Our closure binds the **classical-local** stage (line detector ~6.4 px vs ~5.8 px click noise), which is *stage 2 of their pipeline*, not stage 1. So the two do not conflict. But the thing a CNN-global stage buys — a correct global court proposal — we already obtain on 7/10 by search and 31/38 by reachability. |
| 5 | `yastrebksv/TennisCourtDetector` **repo health**: 3 commits, 4 unanswered issues, weights on Google Drive | **CONFIRMED, first-hand** | Fetched 2026-09-09: **3 commits** on main, **4 open issues**, 272 stars, 69 forks, pretrained weights distributed by **Google Drive link**. I confirmed the issues are *open*; I did **not** confirm they are *unanswered* — that requires opening each one and I did not. |
| 6 | Its **issue #13** worry — the published training script may not reproduce the published numbers | **NOT APPLICABLE. Q1 is answered.** | `backend/weights/court_detector.pt` is dated **Jun 2023 = the upstream RELEASED checkpoint** (lead-established; I could not independently stat the file — no shell this run). `courtnet_ft.pt` (Jul 2026) and `courtnet_split.pt` (Aug 2026) are **our fine-tunes from that checkpoint**. We never ran their training recipe, so a defect in it cannot have touched us. Corroborating and independent of the file date: `_courtnet.py` states it is *"kept byte-for-byte compatible with the published checkpoint"* — a constraint you only impose when you are **loading** their weights, not reproducing their training. |
| 7 | `Gholamreza/tennis_court_keypoints_dataset` — semi-automatic, broadcast-only, selection-biased toward courts classical CV could already nearly solve; and its licence | **SPLIT: one CONFIRMED, one NOT REACHED, and one finding the document missed that matters more than either** | See §4. Broadcast-only: **CONFIRMED**. Licence **MIT**: confirmed on the card. Semi-automatic labelling and the selection effect: **I could not reach evidence for either** — not on the HF card, not in the upstream README. **The finding that outranks both: it is a re-upload of yastrebksv's own 8,841-image training set** — the exact data behind the checkpoint we already fine-tuned from. As training data it carries **zero information we do not already have baked into `court_detector.pt`.** |
| 8 | **CourtSide contradiction:** v1's card cites 85.6% for v0.1 while v0.1's own card says 67.87% | **CONFIRMED as a real discrepancy — and NOT APPLICABLE to court** | See §5. Both figures verified first-hand. But CourtSide is a **YOLOv11n object detector**: v0.1 has a **single class, `tennis_ball`**; v1 has 10 classes and detects the court as **axis-aligned bounding boxes over regions** (court, service boxes, doubles alleys, net, dead zones) — **no lines and no keypoints**. Under COURT ONLY, and for homography specifically, an axis-aligned box over a region that is a *quadrilateral under perspective* carries no shape information. |
| 9 | Its ablation shows **local refinement buys ACCURACY while homography buys RELIABILITY** — they do different jobs | **PARTLY CONFIRMED; the split itself I could not verify** | Upstream README, fetched: base model **0.933 accuracy**, full postprocessed pipeline **0.961** (precision 0.963, median distance 1.83 px). So the postprocessing stack is worth **+2.8 points** in total. I did **not** obtain the per-step rows, so I cannot confirm the claimed division of labour between the refinement step and the homography step. Do not repeat that split as established. |
| 10 | Upstream's **0.963** vs our **~21.6%** | **NEVER COMPARABLE. Q2 is answered — and it is answered twice over.** | §2. |
| 11 | The benchmark paper on amateur court line detection (arXiv **2404.06977**, *Accurate Tennis Court Line Detection on Amateur Recorded Matches*) | **CANNOT BE GRADED — it reports no number in its abstract** | Fetched 2026-09-09: the method is Hough line detection augmented with pretrained shadow-removal and object-detection models. The abstract claims it "can accurately detect lines on amateur, dirty courts" and gives **no numerical accuracy, no dataset size, no camera setup, no evaluation protocol**. I did not fetch the full PDF. **Flagged as the one item here worth a further read**, because it is the only source in the whole document measured on *amateur* footage — which is the trap this project keeps hitting from the other direction. |

---

## 2. Q2, answered: the two numbers were never comparable, on three independent grounds

**Upstream's 0.963 is a per-keypoint precision**, defined as "a keypoint is accurately detected
if the Euclidean distance between the model prediction and the ground truth is less than 7
pixels", at **1280x720**, on a **25% validation split of the same 8,841-image pool it trained
on** — YouTube tournament highlights, frames every 50, manually filtered, all three surfaces.

**Ours is a fire rate on amateur frames** — the fraction of amateur frames on which CourtNet
produces a detection at all. The related held-out figure in `docs/STATE.md` is CourtNet as
**Tier 2 at 20.2% held-out**, against `courtfit` consensus as Tier 1.

They differ on **three axes at once**, any one of which is disqualifying:

1. **Different quantity.** A rate of *firing* versus a rate of *being within 7 px given that it
   fired*. There is no arithmetic that relates them.
2. **Different denominator.** Frames versus keypoints. 14 keypoints per frame, and their metric
   scores each one separately.
3. **Different footage, and this is the largest.** Broadcast tournament highlights versus
   amateur phone video on a 1.38-1.74 m mount. This project's own name for that error is
   *benchmark transfer*, and STATE records that **17 of 20 gold clips had been in training**
   before the court TEST/TRAIN split existed — we have already been burned by exactly this.

**The conclusion survives even if I am wrong about what our number measures.** Suppose 21.6%
*were* per-keypoint precision at 7 px. Comparing it to 0.963 would then be comparing
**out-of-distribution amateur** to **in-distribution broadcast validation** — still not a
comparison. So Q2 is answered whichever way the code reads.

**Honesty flag, because the brief asked me to confirm this *from the code* and I could not.**
With `Glob`/`Grep` dead I could not locate the scoring script (`eval_court.py` is not at
`backend/eval/` or `eval/`; I tried both). The "fire rate" characterisation is carried from
this project's own record and my memory file, **not read off the source this run**. The
argument above is constructed so it does not depend on that reading. If someone wants the
code-level confirmation, it is one `rg` away on a session where the tools work.

---

## 3. The crux, decided

The brief asked me to decide and not hedge. Here is the decision, in the order the argument runs.

### 3.1 The document's diagnosis and its prescription are two different claims, and they get different verdicts

The document says (a) *our failure is a global-search failure* and (b) *therefore reorder to
CNN-global → classical-local*. (a) is a claim about our corpus and is falsifiable by our data.
(b) is a claim about an architecture and is not falsified by (a) being wrong. Collapsing them
is the single biggest error available here, and both of the obvious readings — "court is
closed, so the document is dead" and "the ordering is right, so reopen court" — commit it.

### 3.2 The diagnosis is CONTRADICTED

**Rule 4 — separate the failure modes.** "The search never found it" and "it found it and lost
the vote" are different bugs. On our measured corpus the evidence is one-sided:

| Evidence | Number | Which failure mode it supports |
|---|---|---|
| Reachability (**stopping rule fired**) | nearest seed already within refinement reach on **31 of 38** clips; the brief predicted the opposite in advance | found it |
| Widened seed grid | reaches the courts the old grid could not and **gets every one of them wrong** (26 px, 78 px). STATE's own note: *"the half called a search failure was really scoring"* | found it, lost the vote |
| Criteria vs search | criteria recognise the correct court **9 of 10**; search produces it **7 of 10** | found it |
| Withdrawn `0.18–0.31` | a court a median **5.8 px** from the human clicks clears the accept gate on **9 of 10** clips, not 5 | found it — and the contrary claim is a **withdrawn figure that had already gone out in a previous external research brief** |
| Consensus bar 6/8 → 5/8 | the one 5-vote clip is wrong by **68.7 px** | lost the vote |
| Inter-frame disagreement | **13 of 18** clips disagree principally about court **WIDTH** | lost the vote |
| `verify_court` false rejects | the accept gate's coverage/centrality statistic **orders clips by line VISIBILITY, not correctness** — `yt_match40` (grossly wrong) PASSES at 0.436, above two correct courts | lost the vote |

A global-search explanation cannot account for a candidate that is **generated (7/10)**,
**reachable (31/38)** and **recognised (9/10)**, and then lost at the consensus vote. That is
the definition of the other bug.

**The document's strongest sentence is the one that fails hardest.** "This explains five prior
rejections as one systematic error rather than five dead ends" is attractive precisely because
it is unifying. But at least three of those five were measured **with their own controls and
their own pre-registered gates**, and two of them (reachability, the widened grid) return
results that are *positively inconsistent* with a search failure rather than merely silent on
it. A unifying explanation has to explain the controls too, and this one does not.

### 3.3 The prescription is NOT retired by the court closure — the closure is about a different stage

This is where the document deserves better than the lead feared it would get.

Our closure (`docs/evidence/court-detection-path-after-the-line-ceiling.md`, 2026-09-05) rests
on: the line detector disagrees with truth by ~**6.4 px**, which is the same order as the human
corner-click neighbourhood itself (~**5.8 px**). And the least-squares run proved the fit is
innocent — handed the **perfect** correspondence it drove the line residual to **3.01 px, below
the human homography's own 6.44 px, on 13 of 13 clips**, and reconstruction still got *worse*
(19.80 vs 17.10 px).

**That measurement binds the LOCAL stage.** Upstream's classical refinement, verified from its
README, "extracts white pixels, detects lines, and computes intersections" — it is *the same
class of line evidence* our 6.4 px floor is measured on. So if we adopted their ordering,
**their stage 2 would run straight into our ceiling**, and their +2.8-point gain is measured on
1280x720 broadcast where the paint is crisp and in-distribution.

**It does not bind their stage 1.** CNN global localisation from *appearance* has never been
measured here in that role. So: **the closure and the reordering proposal do not conflict, and
anyone citing the 6.4 px floor to dismiss the reordering is citing the wrong number.** The
lead's instinct on this was right.

### 3.4 So why is the expected value still low, and what would change that

Because **the reordering's payload is exactly the thing we already have.** A CNN-global stage
delivers a correct global court proposal. We generate one on 7/10 and can reach one on 31/38.
Replacing a search that finds the answer with a network that finds the answer does not fix a
vote that then discards it.

**One number would overturn this paragraph, and only one: proposal-stage recall split by
surface.** The pooled 7/10 and 31/38 are across all surfaces. The document's claim is
specifically about **shell** (indoor, trusses, ceiling lights, mesh). If shell proposal recall
is near zero while pooled is 70%, the document is **right about shell** and my §3.2 verdict
should be narrowed to "contradicted outside shell". **That is qa's live measurement and I could
not obtain it** (no message tool, §0b). My verdict stands on the pooled evidence and is
explicitly conditional on that split.

### 3.5 The one court finding here that the document's frame genuinely illuminates

The 2026-09-06 near-baseline+net falsifier found something the document would have predicted
and we did not: **availability binds harder than precision.** Over 40 clips with human corners,
the right doubles sideline is found on **18/40**, the net ground line on **24/40**, and **all
four lines needed for the solve coexist on only 10/40**. Fed *truth* observables the same solve
reproduces the human far-baseline row to **0.007 px median on all 40 clips**. Its own summary:
*"Everything failing is DETECTION."*

That is an evidence-availability failure, and it is the closest thing in this repo to what the
document is describing. It is **not** the same as a global-search failure — the search does not
fail to *rank* the court, it fails to *have the lines at all* — but it is the family the
document is pointing at, and it is the reason I grade the prescription NOT DISPROVEN rather
than dead.

### VERDICT, stated plainly

**The document does not justify reopening court on its central claim, and it is not superseded
either. It is right about one thing and wrong about another, and the two have been welded
together.** Its diagnosis is contradicted by our controls. Its prescription is untouched by our
closure and remains an open architectural question with a low but non-zero expected value,
gated on one number that is being measured right now.

---

## 4. The Gholamreza dataset — what I confirmed, what I could not reach, and the thing that matters more

Fetched `huggingface.co/datasets/Gholamreza/tennis_court_keypoints_dataset`, 2026-09-09.

| Claim in the document | Status | What the source actually says |
|---|---|---|
| Broadcast-only | **CONFIRMED** | Upstream README: "Video highlights from different tournaments" downloaded from YouTube, frames extracted "with step 50 frames". That is broadcast, and it is the disqualifying property for us. |
| Semi-automatic annotation | **NOT CONFIRMED — could not reach** | The HF card does not describe the annotation method at all. The upstream README says frames were "manually filtered". I found no statement of a semi-automatic annotation step in either place. **Do not repeat this as established.** |
| Selection effect — frames where classical CV failed were more likely discarded, biasing the set toward courts classical CV could already nearly solve | **NOT CONFIRMED — could not reach** | Nothing in either card supports or refutes it. "Manually filtered" is a selection step, but its criterion is not stated and its *direction* is unknown. This is a plausible mechanism and a good instinct; it is currently a hypothesis, not a fact. |
| Licence | **CONFIRMED: MIT** | On the re-upload's card. **Caveat worth one line:** a licence asserted on a re-upload is the re-uploader's assertion about someone else's data. The upstream repo is the authority and I did not verify its licence text. |

**The finding that outranks all four.** The card states it is "a re-upload of this dataset" from
a GitHub repository originally on Google Drive, with **8,841 images, 14 annotated points,
1280x720, 75/25 train/val** — those are, digit for digit, yastrebksv's own numbers. **It is the
training set of the checkpoint we already fine-tuned from.**

So as a source of *new* supervision it is worth nothing: every pattern in it is already encoded
in `court_detector.pt`. Fine-tuning on it would be re-fitting to the checkpoint's own training
distribution — moving *away* from amateur footage, not toward it, and inflating any validation
number computed on its split. **If the document proposes this dataset as additional training
data, that recommendation is NOT ACTIONABLE and should be struck.**

---

## 5. CourtSide — the contradiction is real, and it is about the ball

Both cards fetched first-hand, 2026-09-09.

- **`Davidsv/CourtSide-Computer-Vision-v0.1`**: one class, `tennis_ball`. mAP@50 **67.87%**,
  mAP@50-95 24.93%, precision 84.3%, recall 59.5%, evaluated on a **62-image** validation set
  (Viren Dhanwani's 520-image tennis-ball set: 408 train / 62 val / 50 test). YOLOv11n, 2.6M
  params, MIT.
- **`Davidsv/CourtSide-Computer-Vision-v1`**: 10 classes — rackets, tennis balls,
  bottom-dead-zone, court, left/right-doubles-alley, left/right-service-box, net,
  top-dead-zone. mAP@50 **92.13%**, mAP@50-95 85.49%, precision 92.9%, recall 92.0%, on
  "combined datasets" with **no single named benchmark**. YOLOv11n, 2.6M params, MIT.
- The v1 card's reference to a prior ball version at mAP@50 **85.6%** does **not** match v0.1's
  own **67.87%**.

**So the document's flagged contradiction is real as stated.** My reading of the cause, offered
as judgement not fact: a **`v0.2` exists** and 85.6% is most likely v0.2's number mis-attributed
to v0.1. I did not fetch v0.2 to confirm.

**Two things this settles for court, which is what we care about:**

1. **CourtSide detects court REGIONS as axis-aligned boxes, not lines and not keypoints.** A
   service box under perspective is a quadrilateral; its axis-aligned bounding box discards
   exactly the shape information a homography needs. **It cannot calibrate anything.**
2. **Its numbers are self-reported on unnamed combined datasets with no held-out protocol**, and
   the one evaluation with a stated denominator has **n = 62 images**. Nothing here is a
   benchmark; treating 92.13% as evidence of anything would be letting a model grade its own
   homework.

**The one non-zero use, named honestly and not proposed:** a "court" region box *is* a cheap
global appearance prior on where the court is and roughly how wide it is. Our seed grid searches
**0.20-0.42 of frame width while real courts sit at 0.09-0.22** — a range error, and widening it
alone was measured and rejected because scoring then picks wrong. A region prior would constrain
the same range by a different mechanism. **I am not proposing it**: it inherits every problem in
§3.2 (it feeds the search, and the search is not what is failing), it is broadcast-trained, and
its accuracy is unmeasured on anything we would call a benchmark. Recorded so nobody has to
rediscover the idea and re-reject it.

---

## 6. Pre-registered experiment — the only one worth running, and it is gated

**Do not start this before qa's proposal-recall number lands.** It exists only to answer §3.4.

**Question.** Does a CNN-global proposal beat the classical seed search at **proposal recall**
on shell courts specifically?

**Kill condition, checked first, costs nothing.** If qa's proposal recall on **shell** is
already **≥ 70%**, the document's diagnosis is dead outright and **this experiment does not
run.** Say so and close the lane.

**Instrument.** Run `courtnet_split.pt` — the **only** eligible fine-tune, because
`courtnet_ft.pt` (Jul 2026) predates the court TEST/TRAIN split and STATE records that **17 of
20 gold clips had been in training** — on the same 8 consensus frames per clip the classical
path uses. Take its four corner keypoints as a quad.

**Metric.** Proposal recall: the fraction of clips on which the CNN's quad lands within
**20 px@640** of the human corners — i.e. would be an *admissible candidate*. Reported split by
**surface** (Shell / Hardcourt / Clay / Grass) and by **mount height** (≤2.2 m vs >2.2 m, the
net-tape overlap boundary).

**Bar, written before the run.** The reordering is worth building only if CNN proposal recall on
**shell** exceeds classical proposal recall on **shell** by **≥ 20 points** on **≥ 6 shell
clips**. Anything less and the ordering is not the lever.

**Mandatory null control.** A fixed court quad at the corpus-median position and scale, scored
identically. Five gates have failed in this project and several looked fine until a null was
run; a bare "31% recall" is uninterpretable without it.

**What must NOT be measured, and this is the whole discipline of the run.** Do **not** report
keypoint precision in pixels. That is the line-ceiling axis, it is closed by
`least-squares-court-fit.md`, and reporting it would reopen a closed question by accident. This
test measures **proposal**, nothing else.

**Leak guard.** `assert_no_court_gold_leak` must pass in the same run, and the run must state it
did. Rule 4 of CLAUDE.md: a discipline enforced on one model is not enforced on the project.

---

## 7. Feasibility on an A13, on-device — the court CNN is the cheapest thing in this document

Nobody has priced this and it changes how the reordering should be weighed, so I priced it.

**Architecture cost, computed from `_courtnet.py` layer by layer.** VGG-style encoder/decoder,
640x360 in, 15 heatmaps out. Summing MACs across the 18 conv blocks gives **≈151 G MACs ≈ 300
GFLOPs per frame**. That is heavy per frame — but **court detection is one-time**
(`docs/modules.md:130`), 8 frames per video.

- **Sustained throughput is irrelevant here.** 8 frames at setup, once. On an A13's ANE at a
  realistic 20-30% utilisation for a decoder-heavy net, call it 0.2-0.6 s/frame → **~2-5 s
  one-off**. There is no thermal question: this cannot throttle anything because it does not run
  long enough to heat the device. This is the rare case where a peak figure is the honest one,
  and I am saying so rather than hiding it.
- **Operator coverage: zero risk.** The whole network is `Conv2d`, `ReLU`, `BatchNorm2d`,
  `MaxPool2d` and `Upsample(scale_factor=2)` (nearest). BatchNorm folds into the preceding
  convolution at export; nearest-neighbour upsample maps to a core Core ML resize. **Every
  operator is ANE-supported.** No custom layers, no unsupported ops, no fallback to CPU.
- **Size.** ~11M parameters ≈ **22 MB fp16**, ~11 MB int8 — the same order as the ball graph
  already in `mobile/models/`. Per my memory file `coreml-ane-budget`, **int8 buys no speed on
  an A13**, so quantising here is a bundle-size lever only, and given the int8 parity troubles on
  the ball graph I would not quantise a court model without a parity bar.
- **Decode.** Peak-finding over 15 heatmaps at 640x360 must be baked into the graph or done on
  CPU — the exact pattern already solved for the ball model's argmax.

**The strategic point, and it is already in STATE:** the court auto-detect closure explicitly
notes that *"a learned net would in fact be easier to ship than the 2,900-line classical
pipeline, which has no iOS conversion path at all"*, and that closing court **frees that whole
mobile port**. So the iOS ledger runs *against* the closure and *for* the document: if court
auto-detection is ever reopened, **the CNN path is strictly cheaper to ship than the classical
one**, and this section prices it as genuinely cheap. **That is an engineering argument, not an
accuracy argument, and it must not be used as one** — the closure was decided on accuracy and
§3 does not overturn it.

---

## 8. Ranked list of what should actually change here

Ranked by (value × confidence) ÷ cost. Nothing below is a decision; all of it is left open.

1. **Strike the 15th-keypoint recommendation and the duty-cycle recommendation from the
   document.** Both are ALREADY DONE / NOT APPLICABLE, both are cheap for a future reader to
   act on by mistake, and the duty-cycle one would make things **91x worse** if implemented.
   Cost: two lines. Highest value per character in this file.
2. **Get me the source document.** Two of its five open questions are answered above and
   **three I have never seen**. One read closes that. Cost: a file path.
3. **Wait for qa's surface-split proposal recall before backend-dev's reordering goes further.**
   It is the single number that decides whether §3.2 is right, and it is already running. If it
   comes back showing shell proposal recall near zero, my verdict narrows and the reordering
   earns a real run. If it comes back ≥70% on shell, the reordering should stop.
4. **Strike the Gholamreza dataset as a training-data recommendation.** It is the checkpoint's
   own training set (§4). Fine-tuning on it moves us *away* from amateur footage.
5. **Strike CourtSide from the court sections entirely.** It detects balls, rackets and
   axis-aligned court *regions*; it has no lines and no keypoints and cannot calibrate. Its
   85.6/67.87 discrepancy is real but is a ball-model version mix-up (§5).
6. **Read the full PDF of arXiv 2404.06977.** It is the only source in the document measured on
   **amateur** footage and its abstract carries no numbers. ~1 fetch. It is also the only item
   here with a real chance of producing something we have not already measured.
7. **Recover the code-level confirmation of what our ~21.6% measures** on a session where
   `Grep` works. §2's conclusion does not depend on it, but the brief asked for it and I owe the
   gap honestly.
8. **Do NOT re-derive the 6.4 px line ceiling as an argument against the reordering.** It is the
   wrong number for that claim (§3.3) and using it would be a fifth re-proposal in a project
   that has already had nine.

---

## 9. For the PM: the product tradeoff, stated plainly, decision left open

**The document does not put court auto-detection back on the v1 critical path, and it does not
remove the reason it left.** Manual calibration remains the shipped answer and every accuracy
number in this project is measured against it.

What the document *does* put on the table is narrower and it is a **v1.x** question: if court
auto-detection is ever reopened, **the learned path is now the cheap one on iOS** — 8 frames
one-off, ~2-5 s on an A13, every operator ANE-native, ~22 MB fp16, no thermal exposure (§7) —
against a 2,900-line classical pipeline with **no conversion toolchain at all**. The closure
freed that port; reopening re-acquires a cost, but a much smaller one than the port we escaped.

**The tradeoff, in one sentence each:**

- **Hold the closure.** v1 ships manual calibration, the mobile port stays freed, and the ~2-5 s
  of ANE work is never spent. Cost: the user does a setup step, and 57% of existing calibrations
  are below the 2.0-2.2 m net-overlap crossover where that step is *unverifiable in principle*
  — so setup guidance, not court detection, is where the accuracy actually is.
- **Fund the §6 experiment.** One measurement run, gated on qa, with a kill condition that may
  make it free. Buys a defensible answer to "should the court be learned on device", which is
  otherwise going to be re-asked every few sessions. Cost: one run, and the risk that a PASS
  creates pressure to build a lane the accuracy evidence still does not support.

**My read, offered as judgement:** the higher-leverage court work this quarter is not detection
at all — it is the **setup envelope** (get the camera above 2.2 m) and the **live guidance** that
already ships. That is where a measured accuracy gain exists today. But that is a product call
and it is not mine.

---

## 10. Confidence, and what would move it

| Claim | Confidence | What would move it |
|---|---|---|
| The 15th keypoint is already implemented and is upstream's own | **0.98** | Only a misreading of `_courtnet.py`, which I read in full |
| Duty-cycling is NOT APPLICABLE — we are one-time already | **0.95** | If some path re-detects the court per-frame that `modules.md` does not describe. I read the doc, not every call site |
| Q1 retired (we fine-tuned from the checkpoint, not the recipe) | **0.90** | A `stat` on `court_detector.pt` contradicting the Jun 2023 date. I could not run one — no shell |
| Q2 retired (never comparable) | **0.95** | Nothing plausible; the argument holds under both readings of our number (§2) |
| **The diagnosis is CONTRADICTED** | **0.80** | **qa's shell-split proposal recall.** Near-zero on shell narrows me to "contradicted outside shell". This is the cheapest finding to falsify and it is already in flight |
| The prescription is not retired by the line ceiling | **0.90** | Evidence that upstream's *global* stage also depends on line evidence in a way I missed |
| CourtSide cannot calibrate | **0.93** | A v1 output head I did not see on the card |
| Gholamreza = upstream's own training set | **0.88** | Fetching the original GitHub dataset and finding different content behind identical counts |
| A13 court-CNN cost ~2-5 s one-off, zero operator risk | **0.75** | **A measurement on a physical A13, which this project does not own.** My FLOP count is arithmetic; the ANE utilisation factor is judgement. Treat the operator-coverage half (0.90) as much firmer than the timing half (0.6) |

**What would disprove this reconciliation as a whole:** the source document saying something
materially different from the lead's restatement. I graded a summary, not the artifact, and
that is the honest label on all of §1.

---

## 11. Open questions

1. **Q3, Q4 and Q5 of the document are ungraded** because I have never seen them.
2. **Shell-specific proposal recall** — qa has it, I could not ask for it, and it is the one
   number that moves §3.2.
3. **Does upstream's classical refinement gain (+2.8 pts) survive on amateur footage?** Measured
   on broadcast; our line evidence at the same stage carries a 6.4 px floor. Unknown, and it is
   the quantitative form of the §3.3 argument.
4. **The per-step ablation split** — "refinement buys accuracy, homography buys reliability" is
   unverified (§1 item 9).
5. **arXiv 2404.06977's actual numbers**, and what footage they were measured on. The only
   amateur-measured source in the document.
6. **What our ~21.6% is, read off the code** rather than off the project record.
7. Whether the Gholamreza re-upload's MIT licence is the original's licence.
