---
name: reason
description: "Record a task's structured reasoning trace (RENAR)."
context: inline
effort: fast
---

# /reason — Structured Reasoning Trace (RENAR)

Capture *why* you did something, not just *what*. A reasoning trace is an
ordered, append-only chain of steps attached to a task: each step is one of a
closed list of kinds and the four kinds form the canonical RENAR cycle.

**When to use:** at a real decision fork — picking between approaches, adopting
a non-obvious premise, committing to an action whose rationale a fresh agent
would not infer from the diff, or recording how you verified a claim. This is
*not* a per-keystroke journal (that is `task log`); record a step when the
reasoning would otherwise be lost.

## The cycle (closed list — order is canonical)

| kind | answers | example |
|------|---------|---------|
| `intent` | What am I trying to achieve right now? | "Make `task done` close even when no reasoning_steps exist." |
| `premise` | What do I believe/assume that drives the choice? | "Nudge is advisory; QG-2 must not gain a new blocker." |
| `action` | What I'm doing about it | "Add a soft nudge to /task; leave `task_done` gates untouched." |
| `verification` | How I confirmed it worked | "Closed a zero-trace task end-to-end; gates green." |

A trace need not contain all four every time, but a complete fork usually walks
`intent → premise → action → verification`. `seq` auto-increments per task.

## How to record a step

**MCP-first** (preferred):

```
tausik_reason_step(slug="<task-slug>", kind="intent", content="...")
```

CLI fallback:

```bash
.tausik/tausik task reason-step <slug> premise "..."
```

Arguments are positional: `<slug> <kind> <content>`, where `kind` is one of
`intent | premise | action | verification`.

Read the trace back via `tausik_task_show` (MCP, `slug` param) or
`.tausik/tausik task show <slug>` (CLI) — both print the ordered
`Reasoning trace (N)` section alongside plan, decisions, and notes.

## reasoning-step vs task log vs decision

| Surface | Shape | Use for |
|---------|-------|---------|
| `reason-step` | typed (intent/premise/action/verification), ordered | the *reasoning* behind a fork — replayable |
| `task log` | freeform timestamped line | progress journal — "Step 3 done", crash-safety |
| `tausik_decide` | a committed project decision | choices that bind future work, not just this task |

They compose: log the progress, reason the fork, decide the binding. A fork
worth a `reason-step` chain is often also worth a `task log` one-liner so the
timeline reads cleanly.

## Argument dispatch

### $ARGUMENTS = a kind + content (e.g. `intent: …`, `premise: …`)

Record one step on the current active task via `tausik_reason_step`. Find the
active task first if not obvious (`tausik_task_list status="active"`).

### $ARGUMENTS = empty or `show`

Print the current active task's reasoning trace via `tausik_task_show` and
summarise the cycle so far (which kinds are present, what fork is open).

## Rules

- **Append-only.** Steps are never edited or deleted — a wrong premise is
  corrected by a *new* step, not a rewrite. The trace is the audit record.
- **Advisory, never blocking.** Recording reasoning is a discipline, not a gate.
  A task with **zero** reasoning steps still starts and closes normally — QG-0
  and QG-2 do not check the trace.
- **Closed kinds.** Only `intent | premise | action | verification`. An invalid
  kind is rejected by both the service and the DB CHECK constraint.
- **One trace per task.** Steps belong to a task slug; there is no global trace.

## Gotchas

- **Not a journal.** If you find yourself recording a step per file edit, you
  want `task log`. Reason-steps mark *forks*, not activity.
- **`reason-step` needs an existing task** — the slug must resolve. Reasoning
  outside a task belongs in `/explore` findings or a `tausik_decide`.
- **Replayable.** `tausik task replay <slug>` interleaves reasoning steps with
  logs, events, and verification runs into one chronological timeline (and
  `--output FILE` exports it). Write steps that read well out of context.
