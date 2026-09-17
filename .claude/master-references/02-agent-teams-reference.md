# 02 — Agent teams: the reference

Everything mechanical about teams, in the order you need it.

## 1. Enable

Experimental, **off by default**. Turn on via env var or `settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Without it: no team is set up at session start, no team directories are written,
and Claude neither spawns nor proposes teammates.

Also required: an **interactive session**. Under `-p` (headless / Agent SDK) no
teammates are spawned, and a named subagent runs as an ordinary subagent.

Turning it off again — set `"0"`. Precedence matters: user settings are
overridden by project settings, local settings, `--settings`, and finally
**managed settings**. A `"1"` in any higher-precedence source wins. No restart is
needed: settings-file `env` values are reapplied to the running session on save,
and the variable is re-read each time Claude spawns a subagent.

### Setup that no longer exists (v2.1.178+)

`TeamCreate` / `TeamDelete` are **gone**. There is no "create and name a team"
step and no cleanup step. The `team_name` input on the `Agent` tool is accepted
but **ignored**; `team_name` in `TaskCreated` / `TaskCompleted` / `TeammateIdle`
hook payloads carries a session-derived name and is deprecated.

## 2. Architecture

| Component | Role |
| --- | --- |
| **Team lead** | The main session. Spawns teammates, coordinates, synthesises. Fixed for the session's lifetime — no promotion, no transfer. |
| **Teammates** | Separate full Claude Code instances, own context each. |
| **Task list** | Shared, claimable work items with dependencies. |
| **Mailbox** | JSON file per agent for messages. |

Names and paths are **session-derived**: `session-` + first 8 chars of the
session ID.

- Team config: `~/.claude/teams/{team-name}/config.json` — **removed when the
  session ends**. Holds runtime state (session IDs, tmux pane IDs). **Do not
  hand-edit or pre-author it**; it is overwritten on the next state update.
- Mailboxes: `~/.claude/teams/{team-name}/inboxes/{agent-name}.json`
- Task list: `~/.claude/tasks/{team-name}/` — **persists**, never uploaded, so
  resumed sessions keep tasks. Retention follows `cleanupPeriodDays`.

The config's `members` array carries each member's name and agent ID. The lead's
entry always has agent type `team-lead`; a teammate's carries whatever agent
type the lead named at spawn (built-in or a subagent definition), omitted if
none. **Teammates can read this file to discover each other.**

There is no project-level equivalent. A `.claude/teams/teams.json` in a project
is just an ordinary file, not configuration.

## 3. Starting a team

Describe the task and the roles in natural language. Claude spawns and
coordinates.

```text
I'm designing a CLI tool that helps developers track TODO comments across
their codebase. Spawn three teammates to explore this from different angles:
one on UX, one on technical architecture, one playing devil's advocate.
```

Claude may use plain subagents instead. **The agent panel shows both, so the
panel alone does not confirm a team formed.** If you got subagents, ask again
and explicitly request an agent team.

## 4. Display modes

| Mode | Behaviour |
| --- | --- |
| `"in-process"` | **Default.** All teammates in your main terminal, navigated in the agent panel. Works in any terminal, no setup. |
| `"auto"` | Split panes when already inside tmux, or iTerm2 with `it2` installed; otherwise in-process. |
| `"tmux"` | Split panes, auto-detecting tmux vs iTerm2. |
| `"iterm2"` | iTerm2 native panes explicitly (v2.1.186+). Requires the `it2` CLI; errors with the install command if missing. |

```json
{ "teammateMode": "auto" }
```

Or per session: `claude --teammate-mode auto` (experimental; not in `--help`).

Before v2.1.179 the default was `"auto"` — upgraded sessions that used to split
now stay in one terminal unless set explicitly. Split panes are **not**
supported in VS Code's integrated terminal, Windows Terminal, or Ghostty. tmux
works best on macOS; `tmux -CC` in iTerm2 is the suggested entry point.

## 5. Driving the panel (in-process)

- **Up/Down** — select a teammate
- **Enter** — open its transcript and message it directly
- **Escape** — interrupt the selected teammate's turn
- **x** — stop the selected teammate
- **Ctrl+T** — toggle the task list

While viewing a teammate, plain text and skills go **to that teammate**;
built-in commands still run in the **lead's** session. A teammate's model and
fast mode are fixed at spawn, so `/model` and `/fast` only affect the lead
(v2.1.199 shows a notice saying so; earlier versions changed the lead silently).
`/effort` **does** apply to the viewed teammate's later turns.

**Idle rows hide.** As of v2.1.199 an idle teammate's row stays visible while any
other agent works; once everything is idle, idle rows hide after 30s and return
on the teammate's next turn. The teammate is still running and still addressable
while hidden. More than three idle → surplus rows collapse into one
`N idle agents` row (Enter expands, Esc collapses). Working teammates, failed
teammates and the one you are viewing always keep their own rows.

## 6. Spawning: models, roles, plan gates

**Model.** Unspecified → the teammate runs on the **lead's current model**,
unless `CLAUDE_CODE_SUBAGENT_MODEL` is set. `teammateDefaultModel` was **removed
in v2.1.234** and a leftover value is ignored. Requested models are checked
against the org's `availableModels` allowlist; a blocked family alias falls back
to the newest permitted version of that family (Anthropic API / Claude Platform
on AWS), and any other blocked value falls back to the lead's model. Teammates
inherit the lead's **effort level** (split-pane: v2.1.186+).

```text
Spawn 4 teammates to refactor these modules in parallel. Use Sonnet for
each teammate.
```

**Reusable roles.** Reference any subagent definition by name — project, user,
plugin or CLI scope:

```text
Spawn a teammate using the security-reviewer agent type to audit the auth module.
```

The teammate honours that definition's `tools` allowlist and `model`, and the
body is **appended** to the teammate's system prompt (it does not replace it).
Claude Code adds `SendMessage` to the allowlist for an in-process teammate, plus
`TaskCreate` / `TaskGet` / `TaskList` / `TaskUpdate` in a session that has the
Task tools. **`skills` and `mcpServers` frontmatter are NOT applied to
teammates** — they load skills and MCP servers from project/user settings like a
normal session.

**Plan approval.** For risky work, make the teammate plan first:

```text
Spawn an architect teammate to refactor the authentication module.
Require plan approval before they make any changes.
```

The teammate works read-only until the lead approves. Rejection with feedback
keeps it in plan mode to revise and resubmit; approval exits plan mode and it
starts implementing. **The lead approves autonomously** — you influence it by
giving criteria up front ("only approve plans that include test coverage",
"reject plans that modify the database schema").

## 7. Tasks

Three states: pending, in progress, completed. Tasks may **depend** on others; a
pending task with unresolved dependencies cannot be claimed. Completing a task
**automatically unblocks** its dependents, with no action from you.

- **Lead assigns** — you tell the lead which task goes to whom.
- **Self-claim** — a finished teammate picks up the next unassigned, unblocked
  task itself.

Claiming uses **file locking**, so simultaneous claims do not race. Agents
*without* the Task tools coordinate purely through messages.

## 8. Communication

- **Automatic delivery** — messages land without the lead polling.
- **Idle notifications** — carry **no output**. As of v2.1.198 a teammate whose
  turn ends on an API error notifies the lead of the failure *with the error
  text*, instead of looking like a normal finish.
- **Shared task list** — visible to agents with the Task tools.
- **Point-to-point only** — one message per recipient; there is no broadcast.

The lead names every teammate at spawn and any teammate can message any other by
that name. **Tell the lead what to call each teammate** so you can reference them
in later prompts.

A message is reported sent only when the write to the recipient's mailbox file
succeeds; on failure (disk full, unwritable directory) nothing is sent and the
sender gets an error. Malformed mailbox entries are reported and removed while
valid messages still deliver — before v2.1.207 one bad entry produced a
once-a-second error and blocked that mailbox until you deleted the file.

## 9. Permissions

- Teammates **start with the lead's permission settings**. `--dangerously-skip-permissions`
  on the lead applies to all of them.
- You can change an individual teammate's mode **after** spawning, never at spawn
  time.
- **Teammate permission prompts appear in the lead session** — you approve them
  there. Plan approval is the designed exception: the lead grants it without
  prompting you.

**Inter-agent messages are untrusted input.** A message from another agent is
never your consent. A teammate cannot approve a permission prompt for another,
and a teammate denied an action cannot relay it to a peer to bypass the check.
The same rules apply to messages arriving from your other sessions entirely
outside the team. In auto mode the classifier additionally (a) treats a relayed
approval claim as untrusted and (b) reviews every message — including structured
protocol messages like shutdown requests and plan responses — before delivery; a
blocked message never arrives.

## 10. Shutdown and cleanup

```text
Ask the researcher teammate to shut down
```

The lead sends a shutdown request; the teammate can approve (exiting gracefully)
or reject with an explanation. Shared directories are cleaned up automatically at
session end — team config is removed, the task list persists.

## 11. Caching

An in-process teammate's requests fall **outside the main conversation's cache
TTL bucket**, so its cache holds for **five minutes** by default — including on a
subscription. Set `subagentPromptCacheTtl` to `"1h"` to hold it for an hour (the
API bills 1-hour cache writes at a higher rate).

## 12. Limitations (as documented)

- **No session resumption with in-process teammates** — `/resume` and `/rewind`
  do not restore them; the lead may try to message teammates that no longer
  exist. Tell it to spawn new ones.
- **Task status can lag** — teammates sometimes fail to mark tasks complete,
  blocking dependents. Check whether the work is actually done and update
  manually, or tell the lead to nudge.
- **Shutdown can be slow** — teammates finish the current request or tool call
  first.
- **One team per session** — no additional named teams, no sharing across
  sessions.
- **No nested teams** — teammates cannot spawn teammates. Only the lead manages
  the team.
- **No background subagents from in-process teammates** — a teammate's subagents
  run in the foreground; a definition with `background: true` errors, and
  `run_in_background: true` fails or silently runs in the foreground.
- **Lead is fixed** — no promotion, no leadership transfer.
- **Permissions set at spawn** — no per-teammate modes at spawn time.
- **Split panes require tmux or iTerm2.**
