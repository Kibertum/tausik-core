---
name: start
description: "Start session — load status, DB, CLAUDE.md."
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
- `tausik_self_check` MCP tool — verify the running MCP project server is fresh (no stale modules) before any heavy tool call. **If `drift_detected=true` OR `sibling_mcp_count > 0`** stop the parallel batch from being trusted further: warn the user prominently and recommend an IDE restart. See gotchas #77/#79/#80 for the silent-hang failure mode this guards against.

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
2. **MCP Health** — if `tausik_self_check` returned `drift_detected=true` or `sibling_mcp_count > 0`, render a top-of-dashboard `⚠ MCP Health` block: list stale modules with their `delta_seconds`, list sibling PIDs, and recommend `Restart your IDE before continuing` + `Use .tausik/tausik CLI for verify/task done until then`. If clean, render a single OK line or omit the section.
3. **SENAR metrics** from previous work: Throughput, FPSR, DER (if data exists)
4. **Session duration warning** — if `status` shows a warning, highlight it prominently
5. Handoff highlights (if last-handoff has data): what was done, what's blocked, next steps
6. **Dead ends from handoff** — so we don't repeat failed approaches
7. Active tasks (with slugs and titles)
8. Blocked tasks (with blockers)
9. Planning tasks available to pick up
10. **Open exploration** (if any) — warn that it should be ended or continued
11. **Audit status** — if audit is overdue, suggest running `/review` as quality sweep
12. **Memory block** — mention that decisions/conventions/dead ends are loaded; keep them in mind for this session
13. Suggested next action

**If open exploration exists:** Suggest ending it with `/explore end` or continuing it.
**If no tasks exist:** Suggest using `/plan` to create the first task.
**If active tasks exist:** Suggest `/task <slug>` to resume.
**If blocked tasks exist:** Suggest investigating blockers first.

## Code search hierarchy

When you need to locate code during this session, prefer the cheapest tool that fits:

1. **`mcp__codebase-rag__search_code`** — first choice for symbols, patterns, "where is X used", "how does Y work". Returns ranked chunks, not full files. Cheapest token-wise.
2. **`Grep`** — only when you already know which file(s) to search in, or when RAG is empty/stale.
3. **`Read`** — only when you have an exact path. Don't `Read` unfamiliar code — use `search_code` first to locate the relevant chunks.

## Gotchas

- **Session numbering** is auto-incremented. If `session start` fails, the DB might be locked — check `.tausik/tausik.db-wal`.
- **Session duration limit** — SENAR Rule 9.2. If session is already active and over limit, warn prominently and suggest `/end`.
