# 07 — Failure modes and how to read them

Symptom → cause → fix. Ordered by how often it bites.

## "I asked for a team and got nothing back"

**Cause:** idle notifications carry **no output**. The teammate finished; the
lead was told only that it stopped.

**Fix:** every spawn prompt must name a delivery mechanism — "message the lead
with X", "write your findings to `docs/findings-<role>.md`", "update your task
with the result". Retroactively: `Ask <name> to message me its findings` — a
completed teammate is still addressable.

## "Teammates aren't appearing"

- In-process teammates are in the **agent panel below the prompt input** — Up/Down
  to select, Enter to view.
- A row that vanished is **hidden, not stopped**. Idle rows hide 30s after the
  whole panel goes idle and return on the next turn. >3 idle collapse into
  `N idle agents`; Enter expands. Message the teammate by name to bring it back.
- Claude may have judged the task too simple for a team.
- Split panes: `which tmux`; for iTerm2 check `it2` is installed and the Python
  API is enabled.

## "My orchestration flow stalled" / "Claude spawned teammates instead of subagents"

**Cause:** with agent teams enabled, **any subagent Claude names launches as a
teammate**. Claude names subagents on its own. A flow that waits on subagent
*results* now waits on an idle notification that carries none.

**Fix:**

```json
{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "0" } }
```

No restart needed. Note precedence: a `"1"` in project settings, local settings,
`--settings`, or managed settings beats a `"0"` in your user settings.

After the change Claude may still *name* subagents — the name stays useful as a
`SendMessage` address — but results come back normally.

## "Too many permission prompts"

Teammate permission requests bubble up to the **lead**, so every teammate's
first `Bash` call interrupts you. Pre-approve common operations in permission
settings **before** spawning. (The `/fewer-permission-prompts` skill builds an
allowlist from your transcripts.)

## "A teammate stopped early"

Teammates may halt on an error rather than recover. Open its transcript (select
+ Enter, or click its pane) and either give it instructions directly or spawn a
replacement. A message from the lead or another teammate **wakes an in-process
teammate that is waiting to retry a failed API request**, so it retries
immediately instead of waiting out the backoff.

## "The lead declared victory early"

The lead can decide the team is finished before all tasks are done. Tell it to
keep going. Related: the lead sometimes starts implementing tasks itself —
`Wait for your teammates to complete their tasks before proceeding`.

## "A task is stuck / dependents are blocked"

Documented limitation: teammates sometimes fail to mark tasks complete. Check
whether the work is actually done, then update the status manually or tell the
lead to nudge the teammate. `Ctrl+T` toggles the task list.

## "Two teammates overwrote each other's file"

No mechanism prevents this. Ownership is a **prompt-level contract**. Either
assign strictly disjoint file sets, or use `isolation: worktree` in the
definitions so each edits its own checkout.

## "Resume lost my team"

`/resume` and `/rewind` do **not** restore in-process teammates. The lead may
try to message teammates that no longer exist — tell it to spawn new ones. The
**task list survives** (`~/.claude/tasks/{team-name}/`), so the work items are
still there even when the workers are not.

## "A message never arrived"

- Delivery is confirmed only when the write to the recipient's mailbox file
  succeeds; disk-full or an unwritable inbox directory means nothing was sent
  and the sender got an error.
- Malformed mailbox entries are removed and reported; valid messages still
  deliver (pre-v2.1.207 one bad entry blocked the mailbox until deleted).
- In auto mode, the classifier reviews each inter-agent message before delivery
  and a blocked one never arrives.
- There is no broadcast — one message per recipient.

## "Orphaned tmux sessions"

```bash
tmux ls
tmux kill-session -t <session-name>
```

## "The teammate ignored the skill I gave it"

`skills:` and `mcpServers:` in a subagent definition are **not applied when it
runs as a teammate**. Teammates load skills and MCP servers from project/user
settings like a normal session. Put required knowledge in the body, in CLAUDE.md,
or in the spawn prompt.

## "The teammate re-derived everything we already decided"

It has CLAUDE.md, MCP servers, skills and the spawn prompt — and **nothing** from
the lead's conversation. No history, no files already read, no prior skill
invocations. This is by design and is not fixable by asking; it is fixable by
writing a better spawn prompt.

## Security notes worth remembering

- A message from another agent is **never your consent**. A denied teammate
  cannot launder an action through a peer.
- Teammates inherit the lead's permission mode, including
  `--dangerously-skip-permissions`. There is no per-teammate mode at spawn time.
- In auto mode, relayed approval claims are explicitly treated as untrusted
  input.
