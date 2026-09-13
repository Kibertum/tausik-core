**English** | [Русский](../ru/workflow.md)

# Workflow

TAUSIK is designed for pair work: the engineer writes in free form, the AI agent
interprets and executes. No special commands to memorize —
just describe what you want to do.

## Typical Work Day

### Morning: Starting Work

Write to the agent:

```
start working
```

The agent will open a session, show what was done last time, which tasks are in progress,
and suggest what to work on. If there are unfinished tasks — it will offer to continue.

### Working on a Task

For simple tasks — just say what needs to be done:

```
add dark theme to user settings
```

The agent will create a task, formulate acceptance criteria, and start working.

For complex tasks it's better to plan first:

```
let's plan the migration from REST to GraphQL
```

The agent will create a task with a detailed plan, break it into steps,
estimate complexity, and offer to begin.

### Review and Completion

When the work is done:

```
done, review and commit
```

The agent will check the code against a 28-point checklist, run tests and gates,
verify that all acceptance criteria are met, and offer to commit.

### End of Day

```
that's all for today
```

The agent will show the summary: what was done, how many tasks were closed, metrics.
It will save context for the next session — tomorrow you can continue from where you left off.

## Two Work Modes

### Quick (for small tasks)

```
Engineer: "start working"                → /start (opens session)
Engineer: "fix the JWT bug"              → /plan (creates task, plans)
Engineer: "done"                         → /ship (verifies, commits)
```

### Full (for complex tasks)

```
Engineer: "start"                        → /start (context, metrics)
Engineer: "plan the API refactoring"     → /plan (task + plan + AC)
Engineer: "go ahead"                     → /task (QG-0, begins work)
  ... work, progress, dead ends ...
Engineer: "review the code"              → /review (28-item checklist)
Engineer: "run tests"                    → /test
Engineer: "close and commit"             → /ship (QG-2, gates, commit)
Engineer: "that's all for today"         → /end (metrics, handoff)
```

## Quality Gates

TAUSIK automatically checks quality at two points:

**At task start (QG-0):**
- Task goal is formulated
- Acceptance criteria are recorded
- **Blocks** if criteria don't include a negative scenario (error, failure, invalid input)
- Warns for security tasks (auth, payments, PII) without security criteria
- Warns if scope is not defined (what to change / what not to touch)

**At task completion (QG-2):**
- Each acceptance criterion is verified with evidence
- All plan steps are completed
- Tests pass (pytest, ruff, and other gates per stack)
- Warns if knowledge is not documented

These gates cannot be bypassed — the agent cannot start work without a goal
and cannot close a task without verification.

### When Gates Block You

**QG-0 blocks task start:**
- Missing goal → add with `task update <slug> --goal "..."`
- Missing acceptance criteria → add with `task update <slug> --acceptance-criteria "..."`
- No negative scenario in AC → add a criterion like "Returns error on invalid input"
- Session over 180 min → end session with `/end` or extend with `session extend`

**QG-2 blocks task completion:**
- AC not verified → log evidence: `task log <slug> "AC verified: 1. ... ✓ 2. ... ✓"`
- Tests failing → fix the code, tests run automatically on next `task done`
- Plan steps incomplete → mark done with `task step <slug> <N>` or update the plan

The agent handles most of this automatically. If a gate blocks, it will tell you exactly what's missing and how to fix it.

## Hooks — Automatic Control

In addition to Quality Gates, TAUSIK uses Claude Code hooks for real-time control:

- **No code without a task** — attempting to edit a file without an active task is blocked
- **Dangerous command firewall** — `rm -rf`, `DROP TABLE`, `git reset --hard` are blocked
- **Git push only via /ship** — direct `git push` is blocked
- **Auto-format** — code is automatically formatted after each change (ruff, prettier, gofmt)

Details: **[Hooks](hooks.md)**

## Project Memory

TAUSIK saves knowledge between sessions. The agent automatically:

- **Records decisions** — why bcrypt was chosen over argon2
- **Documents dead ends** — what was tried and why it didn't work
- **Captures patterns** — API error format, naming conventions
- **Passes context** — handoff for the next session

This knowledge is loaded at every `/start` and `/task` — the agent doesn't repeat
mistakes from previous sessions.

## Metrics

TAUSIK automatically tracks:

| Metric | What It Shows |
|--------|---------------|
| Throughput | Tasks per session |
| FPSR | Percentage of tasks solved on the first attempt |
| DER | Percentage of tasks where a defect was later found |
| Dead End Rate | Share of dead ends relative to total tasks |
| Lead Time | Average time from creation to task closure |
| Cost per Task | Average time by complexity (simple/medium/complex) |

Metrics help understand: is the agent working efficiently, or spending time on retries?

## Multi-Agent Work

TAUSIK supports multiple AI agents working on the same project simultaneously:

- **Task claiming** — `task claim <slug>` locks a task to a specific agent. Other agents see it as taken and pick a different one. `task unclaim <slug>` releases the lock.
- **No conflicts** — each agent works on its own claimed task. `task next --agent <id>` atomically claims and starts the best available task.
- **Concurrent writes** — the SQLite database runs in WAL (Write-Ahead Logging) mode, so multiple agents can read and write without blocking each other.
- **Shared knowledge** — all agents share the same project memory, decisions, and dead ends. What one agent learns, others see immediately.

No special setup is needed. Just run multiple agent sessions in the same project directory.

## What's Next

- **[Hooks](hooks.md)** — automatic control: blocking, firewall, auto-format
- **[Skills](skills.md)** — full list of what the agent can do
- **[CLI Commands](cli.md)** — if you want to manage TAUSIK from the terminal
- **[Architecture](architecture.md)** — how the framework works internally
