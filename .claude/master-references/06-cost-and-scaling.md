# 06 — Cost and scaling

## The number

> Agent teams use approximately **7x** more tokens than standard sessions when
> teammates run in plan mode, because each teammate maintains its own context
> window and runs as a separate Claude instance.
> — Claude Code docs, *Manage costs effectively*

Token usage scales with **number of active teammates × how long each runs**.
Both halves matter — a teammate you forgot to shut down keeps consuming until it
exits or the session ends.

## The five cost levers, in order of effect

1. **Team size.** Roughly linear. Three focused teammates beat five scattered
   ones, and cost 40% less.
2. **Model.** The docs recommend **Sonnet for teammates** — it balances
   capability and cost for coordination work. Reserve Opus for the lead and for
   teammates doing genuine judgement work. `model: haiku` for mechanical roles.
3. **Runtime.** Shut teammates down when their work is done. Say so explicitly:
   `Ask the <name> teammate to shut down`.
4. **Spawn-prompt size.** Teammates already load CLAUDE.md, MCP servers and
   skills; everything you add to the spawn prompt is in their context from turn
   one and re-sent on every subsequent request. Be specific, not exhaustive.
5. **Cache TTL.** In-process teammates fall outside the main conversation's
   cache bucket — **5-minute TTL by default, even on a subscription**. A
   teammate that thinks for six minutes between turns re-processes its whole
   context. `subagentPromptCacheTtl: "1h"` fixes it; the API bills 1-hour cache
   writes at a higher rate.

## Where usage actually goes

`/usage` on a Pro/Max/Team/Enterprise plan breaks recent usage down by skills,
**subagents**, plugins and MCP servers, each as a percentage, and flags
behaviours accounting for ≥10% (long context, cache misses). Press `d`/`w` to
switch 24h/7d. Figures come from local session history on this machine only.

`/insights` writes an HTML report on *how* you work (friction points,
misunderstood requests) to `~/.claude/usage-data/report.html`.

## Why a long team session keeps burning while idle

Documented causes, all of which apply harder with a team:

- **Long context** — the full conversation is re-sent every request, at the
  cached rate. Multiply by teammate count.
- **Cache misses** — the first message after a break longer than the cache
  lifetime reprocesses everything.
- **Each active teammate** — keeps consuming until it exits.
- **Cross-session messages** — delivered as a new turn in an idle session,
  sending its full context each time.
- **Compaction** — `/compact` reads what it summarises, so compacting a large
  context is itself a large request. `/clear` costs nothing.

## Budget discipline for a team run

Before spawning, write down:

- Number of teammates and their model (`3 × Sonnet` not "some agents").
- The deliverable that ends the run.
- The point at which you shut them down.

During:

- Check `/usage` after the first synthesis. If the team has not produced more
  than a single session would have by then, stop — the shape is wrong, and more
  runtime will not fix it.

After:

- Shut down every teammate explicitly. Idle rows hide after 30s; hidden is not
  stopped.

## The honest comparison

| Approach | Relative cost | Gets you |
| --- | --- | --- |
| Single session | 1x | Sequential depth, full shared context |
| 3 subagents | ~2–3x | Three focused answers, returned to you |
| 3-teammate team | ~5–7x | Three answers **plus** them challenging each other |
| 5-teammate team | ~8–12x | Diminishing: coordination overhead grows superlinearly |

The premium over subagents buys exactly one thing: **inter-agent discussion**.
If the teammates never message each other, you paid the team price for subagent
value.
