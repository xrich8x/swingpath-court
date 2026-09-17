# 04 — Team recipes

Copy-paste team shapes. Each one names the mechanism that makes it work, because
the mechanism is the reason it beats a single session — not the head count.

## Anatomy of a good spawn prompt

Five things, every time:

1. **Role** — the one lens this teammate owns.
2. **Name** — so you can address it later (`Have parser-owner report back`).
3. **Scope** — the exact files/questions it owns, and what it must not touch.
4. **Context it cannot infer** — it has CLAUDE.md and nothing else from your
   conversation.
5. **Deliverable** — what it must send, to whom, in what shape. Without this
   you get an idle notification and no output.

```text
Spawn a teammate named auth-reviewer using the security-reviewer agent type,
with the prompt: "Review the authentication module at src/auth/ for security
vulnerabilities. Focus on token handling, session management, and input
validation. The app uses JWT tokens stored in httpOnly cookies. Report any
issues with severity ratings, and message the lead with your findings when done."
```

---

## Recipe 1 — Parallel review by lens

**Mechanism:** a single reviewer gravitates to one issue class and stops.
Independent lenses each get full attention.

```text
Spawn three teammates to review PR #142:
- One focused on security implications
- One checking performance impact
- One validating test coverage
Have them each review and report findings.
```

Add: *"Each of you message the lead with a numbered findings list, severity
rated, with file:line for each."*

**Best for:** review, audit, "what did we miss".
**Team size:** 3. More lenses overlap.

---

## Recipe 2 — Competing hypotheses (the debate)

**Mechanism:** sequential investigation **anchors** — the first plausible theory
biases everything after it. Investigators actively trying to *disprove each
other* leave only the theory that survives attack.

```text
Users report the app exits after one message instead of staying connected.
Spawn 5 agent teammates to investigate different hypotheses. Have them talk to
each other to try to disprove each other's theories, like a scientific
debate. Update the findings doc with whatever consensus emerges.
```

The critical clause is **"have them talk to each other to try to disprove"** —
without it you get five parallel monologues, which is strictly worse than one
investigation.

**Best for:** root-cause hunts where the cause is genuinely unknown.
**Team size:** 3–5.

---

## Recipe 3 — Disjoint file ownership (parallel build)

**Mechanism:** the only safe way to parallelise implementation is to make file
collisions impossible.

```text
Spawn 3 teammates, one per module. Assign strict file ownership:
- api-owner owns src/api/** only
- ui-owner owns src/components/** only
- test-owner owns tests/** only
No teammate edits a file outside its own set — if you need a change elsewhere,
message the owner. Use Sonnet for each.
```

Consider `isolation: worktree` in the definitions if ownership cannot be made
strictly disjoint.

**Best for:** new modules, cross-layer features.
**Team size:** one per file-set, typically 3.

---

## Recipe 4 — Plan-gated architect

**Mechanism:** for risky refactors, the cheapest failure is one caught before any
file changes.

```text
Spawn an architect teammate to refactor the authentication module.
Require plan approval before they make any changes.
Only approve a plan that keeps the public API unchanged and adds tests for
every branch it touches; reject anything that migrates the schema.
```

The criteria sentence matters — **the lead approves autonomously**, so those are
the only constraints it has.

---

## Recipe 5 — Pipeline with dependencies

**Mechanism:** the shared task list enforces order without you babysitting.
A pending task with unresolved dependencies cannot be claimed; completing a task
auto-unblocks its dependents.

```text
Create tasks: (1) extract the parser interface, (2) port module A to it,
(3) port module B to it, (4) delete the old shim — with 2 and 3 depending on 1,
and 4 depending on both 2 and 3. Spawn two teammates to work the list;
let them self-claim.
```

Watch for the documented lag: teammates sometimes fail to mark tasks complete
and block their dependents. `Ctrl+T` shows the list.

---

## Recipe 6 — Research sweep with distinct angles

**Mechanism:** one agent searching one way misses what a different search angle
would have surfaced.

```text
Spawn 3 teammates to research on-device tennis ball tracking:
- prior-art: papers and benchmark numbers, with the numbers' provenance
- repos: open implementations, license, and what they actually achieve
- skeptic: find the reasons each of the above would fail on amateur phone video
Have the skeptic challenge the other two before anyone reports.
Each of you message the lead with findings AND a confidence level.
```

---

## Steering phrases that fix common drift

| Problem | Say |
| --- | --- |
| Lead starts doing the work itself | `Wait for your teammates to complete their tasks before proceeding` |
| Not enough tasks created | `Split this into smaller tasks — aim for 5-6 per teammate` |
| Lead declares victory early | `Not all tasks are complete. Keep going.` |
| Teammate stalled after an error | Select it, Enter, give it instructions directly — or spawn a replacement |
| Teammate finished but you have no output | `Ask <name> to message me its findings` (idle ≠ delivered) |
| Work is done | `Ask the <name> teammate to shut down` |

## Sizing

- Start with **3–5** teammates. Three focused beat five scattered.
- 15 independent tasks does **not** mean 15 teammates — 3 is a good start.
- Task size: self-contained units with a clear deliverable (a function, a test
  file, a review). Too small and coordination costs more than it saves; too
  large and you find out too late that it went wrong.
- **Start with research and review**, not parallel implementation, if you are new
  to teams — the value shows without the coordination hazards.
