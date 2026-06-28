---
name: task
description: "Work on a task from project DB; track plan steps."
effort: fast
context: inline
---

# /task — Task Execution (SENAR-aligned)

Work on tasks from project DB.
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
   - Read `harness/roles/{role}.md` to understand focus and priorities for this role
   - Read `harness/stacks/{stack}.md` if stack is set — follow stack-specific conventions
   - Load relevant project knowledge via MCP:
     - `tausik_memory_search` with task title keywords
     - `tausik_decisions_list` — recent decisions
   - **Check dead ends** — don't repeat failed approaches:
     - `tausik_memory_list` with `type=dead_end`

3.5. **Brain primer (cross-project, 1.4+).** If `tausik-brain` MCP is configured, run one `brain_search` for patterns and one for gotchas, scoped to the task's topic + stack. Skip silently if brain is disabled.

   ```
   brain_search(
     query="<task title keywords> <stack tag>",
     category="patterns",
     limit=3
   )
   brain_search(
     query="<task title keywords> <stack tag>",
     category="gotchas",
     limit=3
   )
   ```

   Surface up to 3 patterns + 3 gotchas inline before announcing the task. Filter out any page id that appears in `tausik_memory_list type=convention` with title `brain.ignored:<id>` — the user already dismissed it. If a result misleads, mark it ignored via `tausik_memory_quick(type="convention", title="brain.ignored:<page_id>", content="…")` so it does not return next session.

4. **Adopt role** from task — follow the role profile's skill modifiers for /task.

5. **Announce:** Display to user:
   - Role and task title
   - Goal
   - Plan steps as checkboxes
   - Acceptance criteria (numbered)
   - Stack context + role focus

6. **Begin working** through the plan steps sequentially.
   - After each step: `.tausik/tausik task log {slug} "Step N done: description"` + `.tausik/tausik task step {slug} N`
   - **At decision forks — record a reasoning step (RENAR, advisory).** When you
     pick between approaches, adopt a non-obvious premise, or verify a claim,
     capture *why* via `tausik_reason_step` (kind = `intent` | `premise` |
     `action` | `verification`). See `/reason` for the full cycle. This is a
     **soft nudge with escalation, never a gate**:
     - First fork passes with no reasoning step → mention `/reason` once, lightly.
     - A second/third fork still untraced → restate more firmly ("two forks
       untraced — a `reason-step` chain makes this task replayable").
     - The agent may decline; the task **still closes normally with zero
       reasoning steps**. Do not block, do not re-prompt every step.
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
     - **Run verify (Verify-First Contract, v1.4):** `tausik_verify` with `task_slug={slug}` to seed the cache. If verify fails, fix and retry — do NOT proceed to close.
     - Close (preferred, v1.4+): `tausik_task_done` with `slug={slug}`, `ac_verified=true`, `relevant_files=[...]` — instant cache lookup, returns structured `stage` + `blocking_failures` JSON for clean error handling.
     - Close (fallback, legacy MCP servers without v2): `tausik_task_done` with the same arguments — v1 raises a single aggregated error string (1.4 behaviour); iterate fixes, do not silently re-call.
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
| `tausik_task_done` (preferred, v1.4+) | `slug` | `ac_verified=true`, `relevant_files=["f1.py"]`, `evidence`, `no_knowledge=true` — returns structured JSON |
| `tausik_task_done` (legacy fallback) | `slug` | same args; raises aggregated error string on failure |
| `tausik_task_log` | `slug`, `message` | — |
| `tausik_task_step` | `slug`, `step_num` (1-based int) | — |
| `tausik_task_show` | `slug` | — |
| `tausik_task_list` | — | `status="active"`, `epic`, `story`, `stack`, `role`, `limit` |
| `tausik_task_update` | `slug` | `goal`, `acceptance_criteria`, `scope`, `scope_exclude`, `complexity`, `stack`, `role`, `notes` |
| `tausik_reason_step` | `slug`, `kind`, `content` | — (kind: intent\|premise\|action\|verification — advisory RENAR trace) |
| `tausik_dead_end` | `approach`, `reason` | `task_slug`, `tags=["tag"]` |
| `tausik_memory_search` | `query` | — |
| `tausik_memory_list` | — | `type="dead_end"`, `limit` |

## Auto-checkpoint (SENAR Rule 9.3)

After approximately 45 tool calls during a task, remind the user:
"Consider `/checkpoint` to save context — SENAR recommends checkpoints every 30-50 tool calls."

## Code search hierarchy

When investigating code for a task, prefer the cheapest tool that fits:

1. **`mcp__codebase-rag__search_code`** — first choice for symbols, patterns, "where is X used", "how does Y work". Returns ranked chunks, not full files. Cheapest token-wise.
2. **`Grep`** — only when you already know which file(s) to search in, or when RAG is empty/stale.
3. **`Read`** — only when you have an exact path. Don't `Read` unfamiliar code — use `search_code` first to locate the relevant chunks.

## Gotchas

- **QG-0: task start requires goal + AC** — if missing, set them with `task update`. No shortcuts.
- **QG-2: task done requires evidence + --ac-verified** — log AC verification, then close. No shortcuts.
- **Document dead ends** — when an approach fails, use `tausik_dead_end` MCP tool immediately.
- **Only one active task at a time** per agent. `task start` on a second task will fail unless the first is done/blocked.
- **`task step` is 1-indexed**, not 0-indexed. Step numbers must match the plan.
- **`task done` is gated by plan steps** — all steps must be marked done.
- **Always `task log` before `task step`** — log provides context, step just marks completion.
