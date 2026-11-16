---
name: plan
description: "Plan a task — complexity + stack detection."
effort: medium
context: inline
---

# /plan — Task Planning (SENAR-aligned)

Plans a new feature with complexity scoring.

> **Model hint (phase=planning):** plan quality compounds across the whole task,
> so run planning on a strong model — **Fable 5** (or **Opus 4.8**). Do NOT
> downgrade the planner for a "simple" task; complexity does not lower the
> planning tier. Rationale: `docs/ru/research/model-routing-matrix.md`.

## Algorithm

### 0. Interview phase (User Specification)

Before decomposing, gather requirements. This prevents missed requirements and scope drift.

**For complex or vague requests:** invoke the `/interview` skill — it asks **at most 3** clarifying questions (prompt-master "max 3" principle) and stops as soon as answers would no longer change the plan. Prefer it over asking ad-hoc questions.

**Fallback if /interview is not applicable:** ask the user up to 3 clarifying questions covering:
   - Expected behavior: "What should happen when...?"
   - Edge cases: "What if the user does...?"
   - Non-functional requirements: "Any performance/security constraints?"

Then summarize answers into a **user specification** (3-5 bullet points) and confirm: "Is this spec correct? Anything to add?"

**Skip this phase** if the user passes `--skip-interview` or provides a detailed spec upfront (more than 3 sentences describing the feature, or an obviously simple ask).

Fold the user specification into the atomic `tausik_task_add` `rationale`
field (or CLI `--rationale`). Do **not** journal the new slug before
`task start` — an unbound or foreign-bound lease rejects that cross-task
write with `TASK_BINDING_MISMATCH`.

### 1. Analyze scope

1. Which domains are affected? (frontend, backend, database, devops)
2. How many files/components?
3. Risk level?
4. **Is the domain well-known?** If unfamiliar — suggest `.tausik/tausik explore start "..."` first (SENAR Section 5.1).

**Complexity scoring:**
- 1-2 signals: **simple** (1 task)
- 3-5 signals: **medium** (2-3 tasks)
- 6+ signals: **complex** (decompose)

### 2. Check existing knowledge

Use MCP tools:
- `tausik_memory_search` — search for relevant patterns and conventions
- `tausik_memory_list` with `type=dead_end` — don't repeat failed approaches

### 3. Detect stack and load defaults

Determine stack from project structure (package.json, requirements.txt, go.mod). Check `harness/stacks/` for valid names.

**Load defaults from config**: Read `.tausik/config.json` — use `bootstrap.stacks[0]` as default stack. Use `developer` as default role unless task requires otherwise.

### 4. Create task

Epic/story are **optional**. Create executable work with one atomic `task add`.
Do not create it with `task quick` and then call `task update`, `task plan`, or
`task depends`: an execution lease bound to another active task must reject
those cross-task follow-up mutations with `TASK_BINDING_MISMATCH`.

**MCP-first (preferred):** call `tausik_task_add` once with `slug`, `title`,
`goal`, `acceptance_criteria`, `scope`, `scope_paths`, `rollback_plan`,
`call_budget`, `plan_steps`, and `rationale`. When the task follows existing
work, also pass `depends_on`. For a task graph, create tasks in topological
order so every predecessor exists before its dependent.

**CLI fallback:**
```bash
# Full atomic task contract:
.tausik/tausik task add "Task title" --slug my-task --complexity medium --role developer --stack python --goal "What success looks like" --acceptance-criteria "AC-1 succeeds. Negative: invalid input is refused." --call-budget 25 --scope-paths scripts/ tests/ --rollback-plan "git revert" --step "Implement" --step "Verify" --rationale "Why this task exists"

# With epic/story grouping (optional):
.tausik/tausik task add "Task title" --group my-story --slug my-task --complexity medium --role developer --stack python --goal "What success looks like"
```

If the work is part of a larger initiative, create or reuse an epic/story:
```bash
.tausik/tausik epic add <slug> "Epic title"
.tausik/tausik story add <epic-slug> <story-slug> "Story title"
```

### 4b. Estimate tier (agent-native sizing)

Set a tool-call budget during the atomic task-add call — **NOT human hours**. Agents are
measured in tool calls, not wall-clock time. Pick `--call-budget` (preferred,
auto-derives `--tier`) or `--tier` directly.

| Tier | Budget | Real-session example |
|---|---|---|
| `trivial` | ≤10 | one-line config tweak, doc fix, single-arg flag |
| `light` | ≤25 | schema migration + helpers + tests (`agent-units-schema`) |
| `moderate` | ≤60 | recording wiring + hook + service edit + tests |
| `substantial` | ≤150 | CLI + service + MCP + mirror + tests across many files |
| `deep` | ≤400 | full vertical (new stack support, end-to-end feature) |

Use `call_budget=25` on `tausik_task_add`, or `--call-budget 25` on CLI
`task add`. Do not schedule a follow-up update for a newly created task.

Skipping estimation is allowed but flag it explicitly — the task closes
without `call_budget`/`call_actual` data, hurting future tier calibration.

### 5. Set acceptance criteria (SENAR QG-0 MANDATORY)

**CRITICAL: Without acceptance criteria, `task start` will be blocked by QG-0 Context Gate.**

Write clear, verifiable acceptance criteria. Each criterion must be independently testable.

Pass `acceptance_criteria` to the same `tausik_task_add` call, or
`--acceptance-criteria` to CLI `task add`.

**AC quality rules (SENAR):**
- Each criterion independently testable
- At least one negative scenario (error case, boundary)
- No vague criteria ("works correctly", "handles edge cases")

### 6. Set plan steps

Pass `plan_steps=["Step 1", "Step 2", "Step 3"]` to the same MCP task-add
call, or repeat `--step` on CLI `task add`.

### 7. Present plan

Show: task slug, title, complexity, role, **goal**, plan steps, **acceptance criteria**.
Verify: "Goal and AC are set — QG-0 will pass."
Ask: "Proceed with `/task <slug>`?"

**Suggest next:** "Run `/task <slug>` to start working."

## Gotchas

- **Roles are free-text** — use any role name, not limited to a fixed set.
- **Slug format** must be `^[a-z0-9][a-z0-9-]*$`, max 64 chars.
- **Epic/story are optional** — tasks can exist without grouping.
- **QG-0 blocks without goal + AC** — always set both during planning.
- **Defect tasks** — use `--defect-of <parent-slug>` when creating a fix for a bug found in an existing task.
- **Cross-task binding is intentional** — never work around `TASK_BINDING_MISMATCH`; use the atomic creation fields above.
