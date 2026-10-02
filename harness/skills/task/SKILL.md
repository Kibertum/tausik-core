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
   .tausik/tausik task start {slug} --package
   ```
   MCP: `tausik_task_start` with `slug={slug}, package=true`. The successful
   result contains the bounded context package; `started=true, ok=false` means
   activation succeeded but context projection failed, so recover with the
   targeted `task show --package` command named in the result.

   If QG-0 fails (missing goal or acceptance criteria):
   - Set them: `.tausik/tausik task update {slug} --goal "..." --acceptance-criteria "..."`
   - Then retry `.tausik/tausik task start {slug}`

   If the start output recommends a worker route, run `tausik task delegate
   {slug}` and `tausik task handoff {slug}`. On Claude Code or Codex, spawn
   exactly one fresh worker with the returned model, reasoning effort and
   standard speed; pass the handoff contract, and have the worker run `task
   start {slug}` before editing. On Codex, bounded simple/medium work defaults
   to Terra; declared complex work or a named bounded quality failure uses Sol;
   Astra requires `risk=high`. Use paired same-unit `--startup-work` and
   `--remaining-work` estimates to reject uneconomic startup; unknown estimates
   stay unknown. This never switches the model identity of the active task. On
   an advisory/unsupported host, continue in the coordinator and do not claim
   a switch. Never delegate from a worker. The coordinator retains review,
   verification, AC evidence and closure.

2. **Use the context returned by start.** It keeps goal, acceptance criteria,
   paths, plan progress, active decisions, unresolved risk and verify commands together, and
   explicitly reports overflow/omissions. Call `task show --package` only for
   recovery after an explicit context error; use full `task show` only for a
   field the package says it omitted.

   When the next independent reads are already known, collapse them into one
   bounded return: `task show {slug} --work-packet --query "..." --source PATH`.
   MCP uses `tausik_task_show` with `packet` set to a JSON string containing
   `query`, `sources` and `max_bytes`. Every hit carries a source address; inspect
   `overflow` and `omitted` before relying on absence. A refused source stays
   refused — do not retry it through an unscoped reader.

3. **Load role & stack context:**
   - Read `harness/roles/{role}.md` to understand focus and priorities for this role
   - Read `harness/stacks/{stack}.md` if stack is set — follow stack-specific conventions
   - The package already carries task-linked relevant memory and active
     decisions. Search memory or dead ends only when the package is missing
     the fact needed for the current decision.

4. **Adopt role** from task — follow the role profile's skill modifiers for /task.

5. **Announce:** Display to user:
   - Role and task title
   - Goal
   - Plan steps as checkboxes
   - Acceptance criteria (numbered)
   - Stack context + role focus

6. **Begin working** through the plan steps sequentially.
   - After each step, persist the progress note and plan transition together:
     `.tausik/tausik task step {slug} N --message "Step N done: description"`.
     With MCP, pass the same `message` to `tausik_task_step`. The canonical
     composition delegates the existing log and step operations in that order.
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
     - Verify plan completion via `tausik_task_show` with `slug={slug}, mode="package"`
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
.tausik/tausik task step {slug} N --message "Step N completed: description"
```

Find the active task slug first if not obvious from context:
```bash
.tausik/tausik task list --status active
```

The compound call leaves the log durable if the later step transition refuses.

### $ARGUMENTS = empty (no args)

Show current active task status:
```bash
.tausik/tausik task list --status active
```

If one active task — show its bounded details with `task show {slug} --package`.
If none — suggest picking one from planning tasks.

## MCP-first

Prefer MCP tools over CLI bash calls. Exact parameter names:

| MCP Tool | Required Params | Optional Params |
|----------|----------------|-----------------|
| `tausik_task_start` | `slug` | `package=true` |
| `tausik_task_done` (preferred, v1.4+) | `slug` | `ac_verified=true`, `relevant_files=["f1.py"]`, `evidence`, `no_knowledge=true`, `compound='{"message":"final step","step":N,"verify":true}'` |
| `tausik_task_done` (legacy fallback) | `slug` | same args; raises aggregated error string on failure |
| `tausik_task_log` | `slug`, `message` | — |
| `tausik_task_step` | `slug`, `step_num` (1-based int) | `message` logs progress before advancing the step |
| `tausik_task_show` | `slug` | `mode="package"` by default; `mode="full"` only for a named omitted field |
| `tausik_task_list` | — | `status="active"`, `epic`, `story`, `stack`, `role`, `limit` |
| `tausik_task_update` | `slug` | `goal`, `acceptance_criteria`, `scope`, `scope_exclude`, `complexity`, `stack`, `role`, `notes` |
| `tausik_reason_step` | `slug`, `kind`, `content` | — (kind: intent\|premise\|action\|verification — advisory RENAR trace) |
| `tausik_dead_end` | `approach`, `reason` | `task_slug`, `tags=["tag"]` |
| `tausik_memory_search` | `query` | — |
| `tausik_memory_list` | — | `type="dead_end"`, `limit` |

## Auto-checkpoint (SENAR Rule 9.3)

After approximately 45 tool calls during a task, remind the user:
"Consider `/checkpoint` to save context — the checkpoint signal in the tool response says when."

## Code search hierarchy

When investigating code for a task, narrow before you read: `Grep` with a `path`/`glob`, `Read` with `offset`/`limit`. RAG is the route to code: after every `Grep` a hook adds the index's top chunks for the same identifiers, and `mcp__codebase-rag__search_code` answers questions by concept ("where is X handled") that a regex cannot.

Before the first read for a plan step, list the independent questions that step must
answer. Send their searches and bounded reads as one host-native fan-out batch, then
inspect every result before following dependencies. In Codex, use one orchestrator
call for independent operations; elsewhere use the host's batch surface, or parallel
tool calls in one model response when no compound call exists. Do not merge dependent
follow-ups or omit a result merely to reduce the count. Measure model responses and
read-tool calls separately: parallel tools save a response but remain separate tools.

## Gotchas

- **QG-0: task start requires goal + AC** — if missing, set them with `task update`. No shortcuts.
- **QG-2: task done requires evidence + --ac-verified** — log AC verification, then close. No shortcuts.
- **Document dead ends** — when an approach fails, use `tausik_dead_end` MCP tool immediately.
- **Only one active task at a time** per agent. `task start` on a second task will fail unless the first is done/blocked.
- **`task step` is 1-indexed**, not 0-indexed. Step numbers must match the plan.
- **`task done` is gated by plan steps** — all steps must be marked done.
- **Progress precedes the step transition** - use `task step --message` so the
  canonical composition performs `task_log` then `task_step` and reports the
  exact stage if the second operation refuses.
