---
name: checkpoint
description: "Save session snapshot — handoff + CLAUDE.md update."
effort: fast
context: inline
---

# /checkpoint — Context Snapshot (SENAR-aligned)

Quick context save without ending the session.
**When to use:** After completing a task or step, before large operations, and when the checkpoint signal appears in a tool response (the count is derived from the ledger; the threshold is `checkpoint_calls`).

**vs /end:** No session end, no commit prompt. ~4 tool calls vs ~8.

## Algorithm

### 1. Gather state + check session duration

Run in parallel (prefer MCP tools, CLI as fallback):
- `tausik_session_current` MCP tool
- `tausik_task_list` MCP tool with status=active
- `tausik_status` MCP tool
- `git branch --show-current`

> **T1.6 (token-tier1):** memory_block is intentionally NOT re-injected on
> `/checkpoint`. The block was already loaded on `/start` and lives in the
> conversation context. Repeating it on every checkpoint burns ~600 tokens
> per call without adding new information. Use `tausik_memory_search` if you
> need a targeted lookup mid-session.

**Session time is a signal, not a gate** (decision #376): if `status` shows the advisory, mention it once; nothing is refused.

**Slow lane** — only where `.tausik/slow_lane.json` exists (the project's test suite records it): run `pytest -q -m slow` once, in the background, while you do step 2. The default `pytest -q` deselects it and CI does not run on an unpushed branch, so this is the only place it runs. The handoff reads the record itself and says `NOT RUN` or `RED` in `slow_lane`; relay a red lane to the user, do not re-type it.

### 2. Save handoff

Call `tausik_session_handoff` (CLI: `tausik session handoff`). The handoff is
**generated from the journal** — completed tasks, active tasks with their last
log line, verify receipts, decisions, memory, dead ends, open exploration. Do
not re-type what the records already say. Pass only your judgement, if any:

```json
{"next_steps": ["Continue task-slug-2"], "warnings": ["MCP server needs restart"],
 "in_progress": [{"slug": "task-slug-2", "state": "step 3 of 5"}]}
```

These land on top, marked in `authored_fields`.

### 3. Update CLAUDE.md

Use `tausik_update_claudemd` MCP tool to refresh the dynamic section.

### 4. Confirm

Tell the user: "Checkpoint saved. Context preserved for session continuity."

**Suggest next:** "Continue with current task, or `/end` to wrap up the session."

**That's it.** No session close, no commit prompt, no memory saves. Keep it fast.

## Gotchas

- **Authored JSON must be valid JSON** — unescaped quotes in values will break the command. With no authored fields, call it without arguments.
- **Checkpoint does NOT commit** — code changes are only in working tree.
- **Session duration** — an advisory, not a limit (decision #376): mention it, do not stop work for it.
