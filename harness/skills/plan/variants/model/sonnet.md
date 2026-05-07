# /plan — Sonnet overlay

Plan a new task with complexity scoring and stack detection (SENAR-aligned).

## Algorithm

### 0. Interview phase

For complex or vague requests, invoke the `/interview` skill — max 3 clarifying questions, stops when answers stop changing the plan.

**Fallback if /interview is not applicable:** ask up to 3 questions covering expected behavior, edge cases, non-functional requirements. Summarize into a 3-5 bullet user spec, confirm with user.

**Skip** if `--skip-interview`, detailed spec given (>3 sentences), or obviously simple.

Save the user spec via `tausik_task_log` after task creation.

### 1. Analyze scope

1. Domains affected (frontend, backend, db, devops)?
2. File/component count?
3. Risk?
4. Domain familiar? If not — suggest `.tausik/tausik explore start "..."` (SENAR §5.1).

**Complexity:** 1-2 signals → simple, 3-5 → medium, 6+ → complex (decompose).

### 2. Check existing knowledge

- `tausik_memory_search` — relevant patterns/conventions
- `tausik_memory_list type=dead_end` — avoid past failures
- **`brain_search` (cross-project, 1.4+)** — `category="patterns"` and `category="gotchas"`, `limit=3` each, query = task keywords + stack tag. Skip silently if `tausik-brain` MCP missing. Filter out ids that appear in `memory_list type=convention` with title prefix `brain.ignored:`.

### 3. Detect stack and load defaults

Determine stack from project structure (package.json, requirements.txt, go.mod). Validate against `harness/stacks/`.

Read `.tausik/config.json` — use `bootstrap.stacks[0]` as default stack, `developer` as default role.

### 4. Create task

Epic/story are **optional**. For standalone tasks, use `task quick` or `task add` without `--group`.

**MCP-first:**
- Auto-slug: `tausik_task_quick(title="Task title", goal="What success looks like", role="developer", stack="python")`
- Explicit: `tausik_task_add(slug="my-task", title="Task title", goal="...", role="developer", stack="python", complexity="medium")`

**CLI fallback:**
```bash
# Quick (auto-slug):
.tausik/tausik task quick "Task title" --role developer --stack python --goal "What success looks like"

# Full (explicit slug):
.tausik/tausik task add "Task title" --slug my-task --complexity medium --role developer --stack python --goal "..."

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

**MCP-first:** `tausik_task_update(slug="{slug}", call_budget=25)`.

**CLI fallback:**
```bash
.tausik/tausik task update <slug> --call-budget 25
.tausik/tausik task update <slug> --tier light
```

Skipping is allowed but flag explicitly — closing without budget data hurts future tier calibration. `call_actual` records on `task_done`; if `actual > 1.5×budget`, TAUSIK warns for re-calibration.

### 5. Set acceptance criteria (SENAR QG-0 — MANDATORY)

**Without AC, `task start` is blocked by QG-0.**

**MCP-first:** `tausik_task_update(slug="{slug}", acceptance_criteria="1. POST /login returns JWT on valid creds. 2. Returns 401 on invalid password. 3. Returns 422 on missing email.")`

**CLI fallback:** `.tausik/tausik task update <slug> --acceptance-criteria "1. ... 2. ... 3. ..."`

**AC quality rules:**
- Each criterion independently testable
- At least one negative scenario (error case, boundary)
- No vague criteria ("works correctly", "handles edge cases")

### 6. Set plan steps

**MCP-first:** `tausik_task_plan(slug="{slug}", steps=["Step 1", "Step 2", "Step 3"])`

**CLI fallback:** `.tausik/tausik task plan <slug> "Step 1" "Step 2" "Step 3"`

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
