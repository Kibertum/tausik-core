---
name: end
description: "End development session. Records summary, decisions, and handoff to DB. Updates CLAUDE.md. Use when user says 'end session', 'finish', 'wrap up', 'done for today'."
effort: fast
context: inline
---

# /end — Session End (SENAR-aligned)

Archives session, updates CLAUDE.md for next session. Always respond in the user's language.

## Algorithm

### 1. SENAR Metrics Dashboard

Use `tausik_metrics` MCP tool to get metrics.

Display prominently:
- **Throughput**: tasks/session (is it improving?)
- **FPSR**: first-pass success rate (target: >85%)
- **DER**: defect escape rate (target: <5%)
- **Knowledge Capture Rate**: entries/task

### 2. Save Context (delegates to /checkpoint logic)

Run in parallel (MCP-first):
- `tausik_session_current` — get session state
- `tausik_task_list` with `status=active` — find in-progress work
- `tausik_status` — overall project state

Build handoff JSON and save via `tausik_session_handoff` with `handoff={...}`:

```json
{
  "completed": ["task-slug-1: brief description"],
  "in_progress": [{"slug": "task-slug-2", "state": "step 3 of 5"}],
  "key_files": ["scripts/file1.py", "agents/skills/review/SKILL.md"],
  "dead_ends": ["Approach X failed because Y"],
  "next_steps": ["Finish task-slug-2", "Review changes"],
  "warnings": ["MCP server needs restart for new code"]
}
```

**Note:** Handoff MUST be saved while session is still active.

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
- If yes — read `agents/skills/commit/SKILL.md` and follow its full algorithm inline (do NOT launch as subagent — commit needs user confirmation which requires inline context)
- If no — done
- Never force-push or commit without explicit approval

## Gotchas

- **Handoff MUST be saved before `session end`** — once the session is ended, you can't write a handoff to it.
- **Decisions should be recorded before ending** — they're linked to the session.
- **Dead ends must be documented** (SENAR Rule 9.4) — check if any failed approaches weren't recorded.
- **Don't save framework instructions to memory** — only project-specific patterns.

**Final message:** "Session closed. Start a new session with `/start` when ready."
