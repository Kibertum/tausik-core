# /task — Sonnet overlay

Work on tasks from project DB.
**STRICT: Never start coding without running `task start` first.**

## Argument Dispatch

### $ARGUMENTS = task slug

1. **Activate task (QG-0 enforced — NO `--force`):**
   - `tausik_task_start(slug)` (CLI: `.tausik/tausik task start {slug}`)
   - If QG-0 fails (missing goal or AC): set them via `tausik_task_update(slug, goal=..., acceptance_criteria=...)`, then retry.

2. **Load task context:** `tausik_task_show(slug)` → goal, AC, plan steps, role, complexity, stack.

3. **Load role & stack context:**
   - Read `harness/roles/{role}.md` for role focus and priorities.
   - Read `harness/stacks/{stack}.md` if stack set.
   - `tausik_memory_search` with task keywords.
   - `tausik_decisions_list` — recent decisions.
   - `tausik_memory_list type=dead_end` — avoid repeated failures.

3.5. **Brain primer (cross-project, 1.4+).** If `tausik-brain` MCP configured:
   ```
   brain_search(query="<title keywords> <stack tag>", category="patterns", limit=3)
   brain_search(query="<title keywords> <stack tag>", category="gotchas", limit=3)
   ```
   Surface up to 3 patterns + 3 gotchas inline before announcing the task. Filter ids appearing in `tausik_memory_list type=convention` with title `brain.ignored:<id>`. If a result misleads, mark via `tausik_memory_quick(type="convention", title="brain.ignored:<page_id>", ...)`. Skip silently if brain disabled.

4. **Adopt role** — follow the role profile's skill modifiers for /task.

5. **Announce:** role + task title, goal, plan steps as checkboxes, AC numbered, stack + role focus.

6. **Work through plan steps sequentially.**
   - After each step: `tausik_task_log(slug, "Step N done: ...")` + `tausik_task_step(slug, N)`
   - On failure: `tausik_dead_end(approach, reason, task_slug=slug)`, then try alternative.

7. **All steps complete** — suggest `/ship`:
   > "All plan steps done. Run `/ship` to review, test, and close the task."
   Do NOT call `/task done` directly — `/ship` is the standard closing path with full quality checks.

### $ARGUMENTS = "done"

**Redirect to `/ship`** — single closing path with full quality checks.

1. Find active task: `tausik_task_list(status="active")`.
2. Check uncommitted changes: `git status --short`.
3. Redirect:
   - Uncommitted changes → "Launching `/ship` — full review + test + commit cycle." Execute `/ship`.
   - No changes → lightweight close:
     - Verify plan completion via `tausik_task_show(slug)`
     - Walk each AC, log evidence: `tausik_task_log(slug, "AC verified: 1. [criterion] ✓ [evidence] 2. ...")`
     - **Verify-First (v1.4):** `tausik_verify(task_slug=slug)` — seeds cache. If fails, fix and retry.
     - Close (preferred, v1.4+): `tausik_task_done(slug, ac_verified=true, relevant_files=[...])` — structured JSON with `stage` + `blocking_failures`.
     - Close (legacy fallback): `tausik_task_done` with same args — raises aggregated error string; iterate fixes.

**Why redirect?** `/ship` runs full `/review` + `/test` + gates + commit. Closing without review violates SENAR Rule 9.15.

### $ARGUMENTS = "list"

`tausik_task_list` (CLI: `.tausik/tausik task list`) → formatted table with slug, title, status, complexity.

### $ARGUMENTS = "step N"

Mark plan step N done on current active task: `tausik_task_step(slug, step_num=N)` (CLI: `.tausik/tausik task step {slug} N`).

Find active slug first if unclear: `tausik_task_list(status="active")`.

Log progress: `tausik_task_log(slug, "Step N completed: description")`.

### $ARGUMENTS = empty (no args)

Show current active task status: `tausik_task_list(status="active")`. One active → show details with `task_show`. None → suggest picking one from planning tasks.

## MCP-first

Prefer MCP over CLI. Key tools:

| Tool | Required | Optional |
|---|---|---|
| `tausik_task_start` | `slug` | — |
| `tausik_task_done` (v1.4+) | `slug` | `ac_verified`, `relevant_files`, `evidence`, `no_knowledge` |
| `tausik_task_done` (legacy) | `slug` | same args |
| `tausik_task_log` | `slug`, `message` | — |
| `tausik_task_step` | `slug`, `step_num` (1-based) | — |
| `tausik_task_show` | `slug` | — |
| `tausik_task_list` | — | `status`, `epic`, `story`, `stack`, `role`, `limit` |
| `tausik_task_update` | `slug` | `goal`, `acceptance_criteria`, `scope`, `complexity`, `stack`, `role`, `notes` |
| `tausik_dead_end` | `approach`, `reason` | `task_slug`, `tags` |

## Auto-checkpoint (SENAR Rule 9.3)

After ~45 tool calls during a task, remind user:
"Consider `/checkpoint` to save context — SENAR recommends checkpoints every 30-50 tool calls."

## Gotchas

- **QG-0:** goal + AC required for `task start`. No shortcuts.
- **QG-2:** evidence + `ac_verified=true` required for `task done`. No shortcuts.
- **Document dead ends** immediately via `tausik_dead_end`.
- **One active task at a time per agent.** Second `task start` fails until first done/blocked.
- **`task step` is 1-indexed.**
- **`task done` gated by plan steps** — all must be done.
- **Always `task log` before `task step`** — log gives context, step marks completion.
