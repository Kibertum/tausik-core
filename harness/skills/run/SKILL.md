---
name: run
description: "Run the release composition task by task, without stopping."
effort: deep
context: inline
---

# /run — Autonomous execution of the release composition

Close tasks one after another without handing control back between them.

**Why this skill exists.** TAUSIK's autonomy used to be an INSTRUCTION: CLAUDE.md asked the
agent to keep going. MEASURED over one session — 22 tasks closed, 4 of them from the plan
that existed beforehand, 18 filed and closed inside the same session — asking does not work,
and the project's own doctrine says so: a rule that is only asked for gets switched off the
same week. A turn that ends with prose returns control to the user and the agent cannot
resume itself. So continuing has to be a loop inside ONE turn, which is what this is.

## When to use

- The composition is planned and the owner said to work it.
- Overnight or unattended execution.
- After `/plan`, when the slugs are in the DB and nothing needs a decision.

**Do NOT use** for work that needs the owner's judgement mid-implementation: architecture
choices, a risky migration, anything touching money or auth, anything where "which way"
is the question rather than "how". Those go through `/task` one at a time. A driver that
guesses at a judgement call produces work someone has to undo.

## Algorithm

### 1. Arm the run

```bash
export TAUSIK_AUTONOMOUS_BUDGET_BLOCK=1
```

This turns the call budget from advice into a ceiling at 2× — measured over 651 closures,
where the median task lands at 0.58 of its estimate and only 8% pass 2×. Unattended, an
overrun is not information but a session spent on one task.

### 2. Ask the plan, every time

```bash
.tausik/tausik task next
```

**Ask before EVERY task, not once at the start.** Closing a task changes the composition:
it can auto-close a story, unblock a dependant, or surface a defect that outranks what
looked next a minute ago. A list captured up front is stale by its second entry.

Stop the loop when `task next` offers nothing. Its four states are different facts and only
one of them means "keep going":

| State | Meaning | Action |
|---|---|---|
| `ready` | a task is offerable | run it |
| `all-blocked` | everything waits on a predecessor | STOP, name the blockers |
| `all-claimed` | everything belongs to another agent | STOP, say so |
| `empty` | no planning work left | STOP, the composition is done |

### 3. Run one task

Invoke the `/task` skill with the slug. **Never reimplement what it does** — it carries
QG-0, the scope ACL, the context pack, the plan advisory and the model check. A driver that
bypasses them is a driver that closes tasks the gates would have refused.

Then do the work: Read/Edit/Bash/Glob/Grep as the task requires. Do not delegate to a
subagent unless the individual task says to; `/run` is a loop, not a dispatcher.

Close with `task done --ac-verified --verify-handle …` exactly as manual work does.

### 4. Check the ceiling after each close

```bash
.tausik/tausik task budget-check <slug>
```

Non-zero means the task passed 2× its budget. Treat it exactly like a failure — go to
step 5. Silence means fine; the command prints nothing when there is nothing to say.

### 5. Hard-stop on the first failure

Any of these stops the loop: a `ServiceError`, a denied permission prompt, a blocked
`task done` with no legitimate bypass, a red verify that is not a typo, a non-zero
`budget-check`.

```
/run STOPPED at {slug}.
Closed before the stop: {slugs}
Reason: {what failed, verbatim}
Next: task logs {slug} — then fix and /run again; closed tasks are skipped because the
plan no longer offers them.
```

**Never auto-retry. Never silently continue.** A retry that works on the second attempt
hides a flake, and a driver that steps over a failure produces a release nobody can
account for.

### 6. Watch your own capacity

Before starting each task, judge whether there is room to FINISH it. Stopping between
tasks is clean; stopping halfway through one leaves edits nobody can account for, which is
worse than not having started. If room is short: close what is open, write the handoff,
name the next task from the plan, and stop.

### 7. One handoff at the end

`session_handoff` once per run, not once per task — each task already wrote its own. The
summary names `/run`, how many closed, and where it stopped.

## Output

Between tasks, one line each: `{slug}: closed ({calls} calls)`. At the end:

```
/run: {n} closed, stopped at {reason or "composition empty"}. Handoff recorded.
```

Nothing else. Prose between tasks is what ends a turn, and ending a turn is exactly what
this skill exists to avoid.

## What /run does NOT do

- It does not choose tasks — `task next` does, and the composition is the plan.
- It does not skip gates, and it does not pass `--force` to anything.
- It does not file tasks it finds and immediately start them. Filing a finding is free;
  starting it is a departure from the plan, and `task start` will say so.
- It does not ask the owner between tasks. That is the point.

## Gotchas

- **A list of slugs captured up front is stale by its second entry.** Closing a task can
  auto-close a story, unblock a dependant or surface a defect that outranks what looked
  next. Ask `task next` before EVERY task, not once.

- **A turn that ends with prose ends the run.** Control returns to the user and the agent
  cannot resume itself. Between tasks print one line, never a summary — the summary is
  what stops the loop, which is the failure this skill was built against.

- **`budget-check` prints nothing when it is happy.** Read the exit code, not the output:
  a check whose silence means success is invisible to `grep` and obvious to `&&`.

- **The ceiling is armed by an environment variable, so it dies with the shell.** Each
  Bash call in some hosts is its own process; export it in the same command as the check,
  or the run is unarmed and nothing says so.

- **Stopping halfway through a task is worse than not starting it.** Edits without a close
  leave the next agent unable to tell what was verified. Judge room to FINISH before
  starting, and stop between tasks.

- **A red verify is not always a defect.** `bootstrap_drift` after editing `scripts/`
  means the profile was not redeployed — run `python bootstrap/bootstrap.py --ide all`
  and verify again. That is a step, not a failure; a genuine failure is one that survives
  the remediation the gate names.
