---
name: start
description: "Start development session. Loads project status, checks DB, updates CLAUDE.md. Use when user says 'start', 'begin session', 'start work'."
effort: fast
context: inline
---

# /start — Session Start (SENAR-aligned)

Load project context, start session.
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
- `tausik_memory_block` MCP tool — decisions + conventions + recent dead ends (re-inject project memory to prevent drift between sessions)

### Phase 1.5 — Brain primer (cross-project knowledge)

After Phase 1 finishes, run **one** broad `brain_search` call to surface up to 3 cross-project patterns and 3 gotchas relevant to this project's stack. Skip silently if `tausik-brain` MCP is not configured.

```
brain_search(
  query="<comma-separated stack tags from tausik_status, e.g. 'python,fastapi,sqlite'>",
  category="patterns",
  limit=3
)
brain_search(
  query="<same stack tags>",
  category="gotchas",
  limit=3
)
```

When results come back, render them under a `Brain primer` heading in Phase 3 (top-3 patterns + top-3 gotchas, each with one-line description and Notion URL). If the user marks any item as not useful for this project, store the page id locally:

```
tausik_memory_quick(
  type="convention",
  title="brain.ignored:<notion_page_id>",
  content="hidden in /start primer"
)
```

Future `/start` runs filter the primer against `memory_list type=convention title startswith brain.ignored:` so unhelpful tips stop reappearing.

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
11. **Memory block** — mention that decisions/conventions/dead ends are loaded; keep them in mind for this session
12. Suggested next action

**If open exploration exists:** Suggest ending it with `/explore end` or continuing it.
**If no tasks exist:** Suggest using `/plan` to create the first task.
**If active tasks exist:** Suggest `/task <slug>` to resume.
**If blocked tasks exist:** Suggest investigating blockers first.

## Gotchas

- **Session numbering** is auto-incremented. If `session start` fails, the DB might be locked — check `.tausik/tausik.db-wal`.
- **Session duration limit** — SENAR Rule 9.2. If session is already active and over limit, warn prominently and suggest `/end`.
