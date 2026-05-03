**English** | [Русский](../ru/senar.md)

# What is SENAR?

SENAR (Software Engineering Norms for AI-Assisted Research) is an open engineering standard that defines how AI agents should work on software projects. Think of it as a building code for AI-assisted development — a set of rules that make the agent's work predictable, verifiable, and safe.

**Full specification:** [senar.tech](https://senar.tech) | [GitHub](https://github.com/Kibertum/SENAR)

TAUSIK (**T**ask **A**gent **U**nified **S**upervision, **I**nspection & **K**nowledge) is the reference implementation of SENAR. Every rule described below is enforced by TAUSIK automatically — you don't need to read the spec to use the framework.

---

## The Problem SENAR Solves

AI coding agents are powerful but unreliable. Without structure, they:

- Start writing code without defining what "done" means
- Claim tasks are complete without testing
- Forget everything between sessions
- Try the same failed approach three times in a row

AGENTS.md and .cursorrules are recommendations — the agent can ignore them. SENAR provides **enforcement**: hard blocks that physically prevent the agent from skipping steps.

## Core Concepts

### Quality Gates

Two checkpoints that every task must pass:

**QG-0 — Context Gate (before starting work):**
- The task must have a clearly defined goal
- Acceptance criteria must be written down — what counts as "done"
- At least one negative scenario is required (what happens on error, invalid input, etc.)
- Security-sensitive tasks (auth, payments, PII) get an additional warning if security criteria are missing

**QG-2 — Implementation Gate (before closing a task):**
- Every acceptance criterion must have documented evidence (test output, verification steps)
- All plan steps must be completed
- Automated checks must pass (tests, linters — depending on your stack)

These gates are **hard blocks** — the agent literally cannot proceed without meeting the requirements. No `--force` flag, no bypass.

> **Why QG-0 and QG-2, not QG-1?** The numbering follows the SENAR specification: QG-0 runs at task start (before any work), QG-2 runs at task completion (after all work). QG-1 is reserved in the spec for a mid-work checkpoint but is not yet implemented.

### Session Management

Working sessions have structure:

- **Session start** — load context from previous work (what was done, what's blocked, what failed)
- **Session limit (180 min)** — prevents context degradation in long sessions. The agent is blocked from starting new tasks after 3 hours. You can extend with `session extend`.
- **Checkpoints** — periodic context snapshots so nothing is lost if the session crashes
- **Session end** — save a handoff: what was accomplished, what's unfinished, what decisions were made

### Dead End Tracking

When the agent tries an approach and it fails — it records the dead end: what was tried and why it didn't work. Next session, when a similar task comes up, the agent sees the failed approach and avoids repeating it.

### Metrics

Six metrics are tracked automatically, with no manual input:

| Metric | What It Measures |
|--------|------------------|
| **Throughput** | Tasks completed per session |
| **FPSR** (First-Pass Success Rate) | % of tasks solved on the first attempt |
| **DER** (Defect Escape Rate) | % of tasks where a defect was found later |
| **Lead Time** | Average time from task creation to completion |
| **Dead End Rate** | Share of dead ends relative to total tasks |
| **Cost per Task** | Average time by complexity level |

These metrics help answer: is the agent working efficiently, or spending time on retries and dead ends?

## What You'll Notice in Practice

When using TAUSIK, SENAR manifests as:

1. **The agent always asks "what counts as done?"** before writing code — that's QG-0
2. **The agent can't close a task by just saying "done"** — it must show evidence for each criterion — that's QG-2
3. **Starting a new session loads previous context** — you don't explain the project from scratch
4. **Failed approaches are remembered** — the agent won't try the same broken solution twice
5. **Long sessions get a warning** — after 3 hours the agent suggests taking a checkpoint

## SENAR Rules at a Glance

| Rule | What It Says | How TAUSIK Enforces It |
|------|-------------|------------------------|
| Rule 1 | No code without a task | Hook blocks file edits without an active task |
| Rule 2 | Define scope boundaries | Task has `scope` and `scope_exclude` fields |
| Rule 3 | Verify against criteria | QG-0 + QG-2 combined enforcement |
| Rule 7 | Find root cause for defects | Warning if defect task has no root cause in notes |
| Rule 8 | Capture knowledge | Warning at task close if no decisions/patterns recorded |
| Rule 9.2 | Session time limit | Hard block after 180 minutes |
| Rule 9.3 | Periodic checkpoints | Auto-reminder after 40 tool calls |
| Rule 9.4 | Document dead ends | Dedicated tool + reminders in skills |
| Rule 9.5 | Periodic audit | Auto-check at session start |

> **Why do rule numbers skip 4-6?** SENAR covers more than TAUSIK implements. Rules 4 (external review), 5 (verification checklist — partially implemented), and 6 (rollback planning) exist in the spec but are not yet enforced as hard gates. TAUSIK focuses on the rules that have the highest impact on AI agent reliability.

**Full compliance matrix:** [SENAR Compliance Matrix](senar-compliance-matrix.md)

---

## What's Next

- **[Quick Start](quickstart.md)** — set up TAUSIK in 10-15 minutes
- **[Workflow](workflow.md)** — how a typical work day looks
- **[SENAR Compliance Matrix](senar-compliance-matrix.md)** — detailed implementation status for every rule
