# /plan — Sonnet overlay

Plan a new task with complexity scoring and stack detection (SENAR-aligned).

## Algorithm

### 0. Interview phase

For complex or vague requests, invoke the `/interview` skill — max 3 clarifying questions, stops when answers stop changing the plan.

**Fallback if /interview is not applicable:** ask up to 3 questions covering expected behavior, edge cases, non-functional requirements. Summarize into a 3-5 bullet user spec, confirm with user.

**Skip** if `--skip-interview`, detailed spec given (>3 sentences), or obviously simple.

Fold the user spec into the atomic `tausik_task_add` `rationale` field. Do not journal the new slug before `task start`.

### 1. Analyze scope

1. Domains affected (frontend, backend, db, devops)?
2. File/component count?
3. Risk?
4. Domain familiar? If not — suggest `.tausik/tausik explore start "..."` (SENAR §5.1).

**Complexity:** 1-2 signals → simple, 3-5 → medium, 6+ → complex (decompose).

### 2. Check existing knowledge

- `tausik_memory_search` — relevant patterns/conventions
- `tausik_memory_list type=dead_end` — avoid past failures

### 3. Detect stack and load defaults

Determine stack from project structure (package.json, requirements.txt, go.mod). Validate against `harness/stacks/`.

Read `.tausik/config.json` — use `bootstrap.stacks[0]` as default stack, `developer` as default role.

### 4. Create task

Epic/story are **optional**. Use one atomic `task add` for executable work.

**MCP-first:** `tausik_task_add(slug="my-task", title="Task title",
goal="...", acceptance_criteria="...", scope="...", scope_paths=[...],
rollback_plan="...", call_budget=25, plan_steps=[...], rationale="...",
depends_on=[...])`. Omit `depends_on` for a root task. Create graphs in
topological order.

**CLI fallback:**
```bash
# Full atomic contract:
.tausik/tausik task add "Task title" --slug my-task --complexity medium --role developer --stack python --goal "..." --acceptance-criteria "AC-1 succeeds. Negative: invalid input is refused." --call-budget 25 --scope-paths scripts/ tests/ --rollback-plan "git revert" --step "Implement" --step "Verify" --rationale "Why this task exists"

# With epic/story grouping (optional):
.tausik/tausik task add "Task title" --group my-story --slug my-task --complexity medium --role developer --stack python --goal "..."
```

For grouped work:
```bash
.tausik/tausik epic add <slug> "Epic title"
.tausik/tausik story add <epic-slug> <story-slug> "Story title"
```

### 4b. Estimate tier (agent-native sizing)

Set tool-call budget — **NOT human hours**. Pick `--call-budget` (auto-derives `--tier`) or `--tier` directly.

| Tier | Budget |
|---|---|
| trivial | ≤10 |
| light | ≤25 |
| moderate | ≤60 |
| substantial | ≤150 |
| deep | ≤400 |

Put `call_budget=25` in the atomic task-add call.

Skipping is allowed but flag explicitly — closing without budget data hurts future tier calibration. `call_actual` records on `task_done`; if `actual > 1.5×budget`, TAUSIK warns for re-calibration.

### 5. Set acceptance criteria (SENAR QG-0 — MANDATORY)

**Without AC, `task start` is blocked by QG-0.**

Put `acceptance_criteria` in the atomic task-add call.

**AC quality rules:**
- Each criterion independently testable
- At least one negative scenario (error case, boundary)
- No vague criteria ("works correctly", "handles edge cases")

### 6. Set plan steps

Put `plan_steps=["Step 1", "Step 2", "Step 3"]` in the atomic task-add call.

### 7. Present plan

Show: slug, title, complexity, role, goal, plan steps, AC.
Verify: "Goal and AC are set — QG-0 will pass."
Ask: "Proceed with `/task <slug>`?"

## Gotchas

- **Roles are free-text** — not limited to a fixed set.
- **Slug format:** `^[a-z0-9][a-z0-9-]*$`, max 64 chars.
- **Epic/story optional.**
- **QG-0 blocks without goal + AC** — set both during planning.
- **Defect tasks:** use `--defect-of <parent-slug>`.
- **Never work around `TASK_BINDING_MISMATCH`:** task creation carries its whole contract atomically.
