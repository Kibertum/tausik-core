---
name: plan
description: "Plan a new task with complexity scoring and stack detection. Args: [task-description]. Use when user says 'plan', 'create task', 'break down', 'estimate'."
effort: medium
context: inline
---

# /plan — Task Planning (SENAR-aligned)

Plans a new feature with complexity scoring. Always respond in the user's language.

## Algorithm

### 0. Interview phase (User Specification)

Before decomposing, gather requirements through an interactive interview. This prevents missed requirements and scope drift.

1. Ask the user **at least 3 clarifying questions** about:
   - Expected behavior: "What should happen when...?"
   - Edge cases: "What if the user does...?"
   - Non-functional requirements: "Any performance/security constraints?"
   - Integration points: "What existing systems does this touch?"
2. Summarize answers into a **user specification** (3-5 bullet points).
3. Confirm with the user: "Is this spec correct? Anything to add?"

**Skip this phase** if the user passes `--skip-interview` or provides a detailed spec upfront (more than 3 sentences describing the feature).

Save the user specification via `tausik_task_log` after task creation.

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

Determine stack from project structure (package.json, requirements.txt, go.mod). Check `agents/stacks/` for valid names.

**Load defaults from config**: Read `.tausik/config.json` — use `bootstrap.stacks[0]` as default stack. Use `developer` as default role unless task requires otherwise.

### 4. Create task

Epic/story are **optional**. For standalone tasks, use `task quick` or `task add` without `--group`.

**MCP-first (preferred):**
- Auto-slug: `tausik_task_quick` with `title="Task title"`, `goal="What success looks like"`, `role="developer"`, `stack="python"`
- Explicit slug: `tausik_task_add` with `slug="my-task"`, `title="Task title"`, `goal="..."`, `role="developer"`, `stack="python"`, `complexity="medium"`

**CLI fallback:**
```bash
# Quick (auto-slug):
.tausik/tausik task quick "Task title" --role developer --stack python --goal "What success looks like"

# Full (with explicit slug):
.tausik/tausik task add "Task title" --slug my-task --complexity medium --role developer --stack python --goal "What success looks like"

# With epic/story grouping (optional):
.tausik/tausik task add "Task title" --group my-story --slug my-task --complexity medium --role developer --stack python --goal "What success looks like"
```

If the work is part of a larger initiative, create or reuse an epic/story:
```bash
.tausik/tausik epic add <slug> "Epic title"
.tausik/tausik story add <epic-slug> <story-slug> "Story title"
```

### 5. Set acceptance criteria (SENAR QG-0 MANDATORY)

**CRITICAL: Without acceptance criteria, `task start` will be blocked by QG-0 Context Gate.**

Write clear, verifiable acceptance criteria. Each criterion must be independently testable.

**MCP-first:** `tausik_task_update` with `slug="{slug}"`, `acceptance_criteria="1. POST /login returns JWT on valid creds. 2. Returns 401 on invalid password. 3. Returns 422 on missing email."`

**CLI fallback:**
```bash
.tausik/tausik task update <slug> --acceptance-criteria "1. POST /login returns JWT on valid creds. 2. Returns 401 on invalid password. 3. Returns 422 on missing email."
```

**AC quality rules (SENAR):**
- Each criterion independently testable
- At least one negative scenario (error case, boundary)
- No vague criteria ("works correctly", "handles edge cases")

### 6. Set plan steps

**MCP-first:** `tausik_task_plan` with `slug="{slug}"`, `steps=["Step 1", "Step 2", "Step 3"]`

**CLI fallback:**
```bash
.tausik/tausik task plan <slug> "Step 1" "Step 2" "Step 3"
```

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
