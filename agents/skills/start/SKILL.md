---
name: start
description: "Start development session. Loads project status, checks DB, updates CLAUDE.md. Use when user says 'start', 'begin session', 'start work'."
effort: fast
context: inline
---

# /start — Session Start (SENAR-aligned)

Load project context, start session. Always respond in the user's language.

## Algorithm

**3 phases. Batch parallel calls aggressively.**

### Phase 1 — Open Session + Gather State

Check that `.tausik/tausik.db` exists. If not — tell the user to run bootstrap first: `python .tausik-lib/bootstrap/bootstrap.py --init`. Stop here until DB exists.

Run in parallel (prefer MCP tools, CLI as fallback):
- `tausik_session_start` MCP tool
- `tausik_status` MCP tool
- `tausik_session_last_handoff` MCP tool
- `tausik_task_list` MCP tool with status=active,blocked,planning
- `tausik_metrics` MCP tool
- `tausik_explore_current` MCP tool
- `tausik_audit_check` MCP tool

### Phase 2 — Update CLAUDE.md

Use `tausik_update_claudemd` MCP tool to refresh the dynamic section.

### Phase 3 — Present Dashboard

Show the user a summary:
1. Session number and status
2. **SENAR metrics** from previous work: Throughput, FPSR, DER (if data exists)
3. **Session duration warning** — if `status` shows a warning, highlight it prominently
4. Handoff highlights (if last-handoff has data): what was done, what's blocked, next steps
5. **Dead ends from handoff** — so we don't repeat failed approaches
6. Active tasks (with slugs and titles)
7. Blocked tasks (with blockers)
8. Planning tasks available to pick up
9. **Open exploration** (if any) — warn that it should be ended or continued
10. **Audit status** — if audit is overdue, suggest running `/review` as quality sweep
11. Suggested next action

**If open exploration exists:** Suggest ending it with `/explore end` or continuing it.
**If no tasks exist:** Suggest using `/plan` to create the first task.
**If active tasks exist:** Suggest `/task <slug>` to resume.
**If blocked tasks exist:** Suggest investigating blockers first.

## Gotchas

- **Session numbering** is auto-incremented. If `session start` fails, the DB might be locked — check `.tausik/tausik.db-wal`.
- **Session duration limit** — SENAR Rule 9.2. If session is already active and over limit, warn prominently and suggest `/end`.
