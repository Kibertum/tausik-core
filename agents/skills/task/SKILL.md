---
name: task
description: "Work on task from project DB. Tracks progress via plan steps. Args: [task-slug|done|list|step N]. Use when user says 'task', 'work on', 'take task', 'task done'."
effort: fast
context: inline
---

# /task — Task Execution (SENAR-aligned)

Work on tasks from project DB. Always respond in the user's language.

**STRICT: Never start coding without running `task start` first.**

## Argument Dispatch

### $ARGUMENTS = task slug

1. **Activate task (QG-0 enforced — NO --force):**
   ```bash
   .tausik/tausik task start {slug}
   ```
   If QG-0 fails (missing goal or acceptance criteria):
   - Set them: `.tausik/tausik task update {slug} --goal "..." --acceptance-criteria "..."`
   - Then retry `.tausik/tausik task start {slug}`

2. **Load task context:**
   ```bash
   .tausik/tausik task show {slug}
   ```
   Extract: goal, acceptance criteria, plan steps, role, complexity, stack.

3. **Load role & stack context:**
   - Read `agents/roles/{role}.md` to understand focus and priorities for this role
   - Read `agents/stacks/{stack}.md` if stack is set — follow stack-specific conventions
   - Load relevant project knowledge via MCP:
     - `tausik_memory_search` with task title keywords
     - `tausik_decisions_list` — recent decisions
   - **Check dead ends** — don't repeat failed approaches:
     - `tausik_memory_list` with `type=dead_end`

4. **Adopt role** from task — follow the role profile's skill modifiers for /task.

5. **Announce:** Display to user:
   - Role and task title
   - Goal
   - Plan steps as checkboxes
   - Acceptance criteria (numbered)
   - Stack context + role focus

6. **Begin working** through the plan steps sequentially.
   - After each step: `.tausik/tausik task log {slug} "Step N done: description"` + `.tausik/tausik task step {slug} N`
   - **On failure/dead end:** Document it immediately:
     ```bash
     .tausik/tausik dead-end "What was tried" "Why it failed" --task {slug}
     ```
     Then try an alternative approach.

7. **When all steps complete** — suggest `/ship`:
   > "All plan steps done. Run `/ship` to review, test, and close the task."

   Do NOT suggest `/task done` directly — `/ship` is the standard closing path with full quality checks.

### $ARGUMENTS = "done"

**Redirect to `/ship`** — the single path for closing tasks with full quality checks.

1. **Find active task:**
   Use `tausik_task_list` MCP tool with `status=active`.

2. **Check for uncommitted changes:**
   ```bash
   git status --short
   ```

3. **Redirect:**
   - If uncommitted changes exist → tell the user: "Launching `/ship` — full review + test + commit cycle." Then execute the `/ship` skill.
   - If no changes (everything already committed) → run a lightweight close:
     - Verify plan completion via `tausik_task_show` with `slug={slug}`
     - Walk each AC, log evidence: `tausik_task_log` with `slug={slug}`, `message="AC verified: 1. [criterion] ✓ [evidence] 2. ..."`
     - Close: `tausik_task_done` with `slug={slug}`, `ac_verified=true`, `relevant_files=[...]`
     - Announce completion

**Why redirect?** `/ship` runs full `/review` + `/test` + gates + commit. Closing without review violates SENAR Rule 9.15 (AI Output QA).

### $ARGUMENTS = "list"

Show all tasks:
```bash
.tausik/tausik task list
```

Display as a formatted table with slug, title, status, and complexity.

### $ARGUMENTS = "step N"

Mark plan step N as done on the current active task:
```bash
.tausik/tausik task step {slug} N
```

Find the active task slug first if not obvious from context:
```bash
.tausik/tausik task list --status active
```

Log progress: `.tausik/tausik task log {slug} "Step N completed: description"`

### $ARGUMENTS = empty (no args)

Show current active task status:
```bash
.tausik/tausik task list --status active
```

If one active task — show its details with `task show {slug}`.
If none — suggest picking one from planning tasks.

## MCP-first

Prefer MCP tools over CLI bash calls. Exact parameter names:

| MCP Tool | Required Params | Optional Params |
|----------|----------------|-----------------|
| `tausik_task_start` | `slug` | — |
| `tausik_task_done` | `slug` | `ac_verified=true`, `relevant_files=["f1.py"]`, `no_knowledge=true` |
| `tausik_task_log` | `slug`, `message` | — |
| `tausik_task_step` | `slug`, `step_num` (1-based int) | — |
| `tausik_task_show` | `slug` | — |
| `tausik_task_list` | — | `status="active"`, `epic`, `story`, `stack`, `role`, `limit` |
| `tausik_task_update` | `slug` | `goal`, `acceptance_criteria`, `scope`, `scope_exclude`, `complexity`, `stack`, `role`, `notes` |
| `tausik_dead_end` | `approach`, `reason` | `task_slug`, `tags=["tag"]` |
| `tausik_memory_search` | `query` | — |
| `tausik_memory_list` | — | `type="dead_end"`, `limit` |

## Auto-checkpoint (SENAR Rule 9.3)

After approximately 45 tool calls during a task, remind the user:
"Consider `/checkpoint` to save context — SENAR recommends checkpoints every 30-50 tool calls."

## Gotchas

- **QG-0: task start requires goal + AC** — if missing, set them with `task update`. No shortcuts.
- **QG-2: task done requires evidence + --ac-verified** — log AC verification, then close. No shortcuts.
- **Document dead ends** — when an approach fails, use `tausik_dead_end` MCP tool immediately.
- **Only one active task at a time** per agent. `task start` on a second task will fail unless the first is done/blocked.
- **`task step` is 1-indexed**, not 0-indexed. Step numbers must match the plan.
- **`task done` is gated by plan steps** — all steps must be marked done.
- **Always `task log` before `task step`** — log provides context, step just marks completion.
