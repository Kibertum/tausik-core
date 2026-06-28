**English** | [Русский](/ru/docs/reasoning-trace)

# Reasoning Trace (RENAR)

A **reasoning trace** is an ordered, append-only chain of typed steps attached to
a task. It records *why* the agent did something — the rationale a fresh agent
could not reconstruct from the diff alone. It is the reasoning half of RENAR
reproducibility (the other halves are events, verification runs, and receipts).
The trace is read on its own via `tausik task show`; `tausik task replay <slug>`
produces a fuller chronological timeline that interleaves all four sources.

The `/reason` skill is the agent-facing surface; this page is the reference.

## The four kinds (closed list)

Steps are one of a closed list of kinds. The four form the canonical cycle and
`seq` auto-increments per task:

| kind | answers |
|------|---------|
| `intent` | What am I trying to achieve right now? |
| `premise` | What belief/assumption drives the choice? |
| `action` | What I'm doing about it |
| `verification` | How I confirmed it worked |

An invalid kind is rejected twice — once by the service (friendly error) and
again by the DB `CHECK` constraint (hard guarantee), so a malformed step is
never silently stored.

## Recording steps

MCP-first (preferred):

```
tausik_reason_step(slug="my-task", kind="intent", content="…")
```

CLI fallback — arguments are positional `<slug> <kind> <content>`:

```bash
.tausik/tausik task reason-step my-task intent "…"
```

Read the trace back via CLI — `.tausik/tausik task show my-task` — or MCP —
`tausik_task_show(slug="my-task")`. Both print a `Reasoning trace (N)` section
after plan and decisions.

## Worked example — a full trace

The trace below is from `v16r-reason-skill` itself: shipping a `/reason` skill
whose nudge must *not* become a new gate.

```bash
.tausik/tausik task reason-step v16r-reason-skill intent \
  "Ship a /reason skill + a /task nudge that records reasoning at forks."

.tausik/tausik task reason-step v16r-reason-skill premise \
  "Reasoning capture is a discipline, not a gate — QG-2 must gain no new blocker."

.tausik/tausik task reason-step v16r-reason-skill action \
  "Add an escalating SOFT nudge to /task step 6; leave task_done gates untouched."

.tausik/tausik task reason-step v16r-reason-skill verification \
  "Closed a task with zero reasoning steps end-to-end — task done succeeded, no new gate fired."
```

Rendered by `tausik task show v16r-reason-skill`:

```
Reasoning trace (4):
  1. (intent) Ship a /reason skill + a /task nudge that records reasoning at forks.
  2. (premise) Reasoning capture is a discipline, not a gate — QG-2 must gain no new blocker.
  3. (action) Add an escalating SOFT nudge to /task step 6; leave task_done gates untouched.
  4. (verification) Closed a task with zero reasoning steps end-to-end — task done succeeded, no new gate fired.
```

The chain reads as a self-contained argument: the **intent** states the goal,
the **premise** names the constraint that shaped the design, the **action**
records the concrete choice, and the **verification** closes the loop by
testing the very constraint the premise asserted. A correction never edits a
prior step — append a new step (often a fresh `premise`) instead.

## When to record — and when not to

Record a step at a **fork**: choosing between approaches, adopting a non-obvious
premise, or verifying a claim whose rationale would otherwise be lost.

Do **not** use it as a per-edit journal — that is `task log`. Three surfaces,
three jobs:

| Surface | Shape | Use for |
|---------|-------|---------|
| `reason-step` | typed, ordered, append-only | the *reasoning* behind a fork — replayable |
| `task log` | freeform timestamped line | progress journal, crash-safety |
| `tausik_decide` | a committed project decision | choices that bind future work |

## Guarantees

- **Append-only.** Steps are never edited or deleted; the trace is an audit
  record. Wrong premise → new step, not a rewrite.
- **Advisory, never blocking.** Neither QG-0 (`task start`) nor QG-2
  (`task done`) inspects the trace. A task with **zero** reasoning steps starts
  and closes normally — the `/task` nudge is a soft, escalating reminder only.
- **One trace per task.** Steps are scoped to a task slug; there is no global
  trace.

## See also

- **[Skills](skills.md)** — `/reason` and the rest of the skill surface
- **[Workflow](workflow.md)** — how reasoning fits the task lifecycle
- **[CLI Commands](cli.md)** — `task reason-step`, `task replay`
- **[MCP Tools](mcp.md)** — `tausik_reason_step`, `tausik_task_replay`
