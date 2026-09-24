---
name: end
description: "End session — handoff + decisions + CLAUDE.md."
effort: fast
context: inline
---

# /end — Session End (SENAR-aligned)

Archives session, updates CLAUDE.md for next session.
## Algorithm

### 1. SENAR Metrics Dashboard

Use `tausik_metrics` MCP tool to get metrics.

Display prominently:
- **Throughput**: tasks/session (is it improving?)
- **FPSR**: first-pass success rate
- **DER**: defect escape rate
- **Targets**: quote the report's `target … (basis: …)` lines as printed. Do not
  restate a number from memory: a target without its basis is not a target
  (SENAR 1.5 §9.4(c)). A `CROSSED` line is escalated to the owner, not moved.
- **Knowledge Capture Rate**: entries/task

### 2. Save Context (delegates to /checkpoint logic)

Run in parallel (MCP-first):
- `tausik_session_current` — get session state
- `tausik_task_list` with `status=active` — find in-progress work
- `tausik_status` — overall project state

Call `tausik_session_handoff` (CLI: `tausik session handoff`). The handoff is
**generated from the journal** — completed tasks, active tasks with their last
log line, verify receipts, decisions, memory, dead ends, open exploration. Do
not re-type what the records already say. Pass only your judgement, if any:

```json
{"next_steps": ["Continue task-slug-2"], "warnings": ["MCP server needs restart"],
 "in_progress": [{"slug": "task-slug-2", "state": "step 3 of 5"}]}
```

These land on top, marked in `authored_fields`.

**Note:** `session end` generates the handoff itself when none was written in the session, so a session never ends without one (SENAR §7.3).

### 3. Record Decisions

If any architectural or design decisions were made during the session, use `tausik_decide` with `decision="We chose X over Y"`, `rationale="Because Z"`, optionally `task_slug="{slug}"`.

### 4. Save Patterns and Dead Ends

If any reusable patterns, gotchas, or dead ends were discovered:
- Use `tausik_memory_add` with `type="pattern"` (or gotcha/convention/context/dead_end), `title="Short title"`, `content="Detailed description"`, optionally `tags=["tag"]`, `task_slug="{slug}"`
- **SENAR Rule 9.4:** If any approach failed and was NOT already documented, use `tausik_dead_end` MCP tool

Only save project-specific patterns — not framework instructions.

### 5. End Session

Use `tausik_session_end` with `summary="Completed X, fixed Y, planned Z"`.

### 6. Update CLAUDE.md

Use `tausik_update_claudemd` MCP tool to refresh the dynamic section.

### 7. Git Commit Prompt

Ask the user: "Commit changes? (y/n)"
- If yes — read `harness/skills/commit/SKILL.md` and follow its full algorithm inline (do NOT launch as subagent — commit needs user confirmation which requires inline context)
- If no — done
- Never force-push or commit without explicit approval

## Gotchas

- **Authored next steps go in before `session end`** — the generated part is written by `session end` anyway; your judgement is not.
- **Decisions should be recorded before ending** — they're linked to the session.
- **Dead ends must be documented** (SENAR Rule 9.4) — check if any failed approaches weren't recorded.
- **Don't save framework instructions to memory** — only project-specific patterns.

**Final message:** "Session closed. Start a new session with `/start` when ready."
