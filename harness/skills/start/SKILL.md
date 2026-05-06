---
name: start
description: "Start session — load status, DB, CLAUDE.md."
effort: fast
context: inline
---

# /start — Session Start (SENAR-aligned)

Load project context, start session. **Token-economy: minimum work, maximum signal.**

## Algorithm

### Phase 1 — Open + gather (one parallel batch)

Check `.tausik/tausik.db` exists. If not — tell user: `python .tausik-lib/bootstrap/bootstrap.py --init`. Stop.

Run **these 5 MCP tools in one parallel batch** (no other phases until they all return):

- `tausik_session_start`
- `tausik_status` with `compact: true`
- `tausik_session_last_handoff`
- `tausik_task_list` with `status=active,blocked` (planning is in CLAUDE.md already)
- `tausik_self_check`

Skip these by default — they bloat context without commensurate signal:
- `tausik_metrics` — pull only on user request (`/metrics`)
- `tausik_explore_current` — `tausik_status` already flags open exploration
- `tausik_audit_check` — `tausik_status` already shows audit overdue
- `tausik_memory_block` — content lives in CLAUDE.md "Current State" via `update_claudemd`

### Phase 2 — Update CLAUDE.md

Call `tausik_update_claudemd`. This refreshes the dynamic section AND injects compact memory tail (recent decisions + conventions + dead ends, one line each) so memory persists across sessions without a separate re-injection call.

### Phase 3 — Present Dashboard (under 800 tokens)

Render in this order, **omit empty sections silently**:

1. **MCP Health** — only if `self_check` returned `drift_detected=true` or `sibling_mcp_count > 0`: list stale modules + sibling PIDs, recommend IDE restart + CLI fallback. If clean, omit entirely (don't write "OK").
2. **Session** — number + active-time warning if status flagged it.
3. **Handoff highlights** — if `last_handoff` has data: 1-line "done", 1-line "blocked", 1-line "next". Skip if empty.
4. **Active tasks** — slug + title, one per line. Skip if none.
5. **Blocked tasks** — slug + blocker reason, one per line. Skip if none.
6. **Suggested next action** — one sentence:
   - open exploration → "End or continue with `/explore`"
   - active tasks → "Resume with `/task <slug>`"
   - blocked → "Investigate blocker on `<slug>`"
   - clean slate → "`/plan` to create the first task"

Do **not** render: planning tasks list (use `/next` on demand), metrics block, audit reminder (status surfaces it), "Memory block loaded" notice (it's in CLAUDE.md).

## Brain primer — opt-in only

Brain primer (cross-project knowledge from `tausik-brain`) is **not** in the default `/start` flow because:
- It costs 2 HTTP round-trips to Notion on local-index shortfall.
- Most session starts don't need cross-project context — only kickoffs of a new feature do.

If user invokes `/start --brain` or asks "what does the brain say about X", run:

```
brain_search(query="<stack-tags-or-feature-words>", category="patterns", limit=3)
brain_search(query="<same-query>", category="gotchas", limit=3)
```

`brain_search` already fails fast (5s timeout) and returns local-only results on Notion failure — never blocks.

If `tausik-brain` MCP is not configured: skip silently, no warning, no fallback. The primer is opt-in by design.

## Code search hierarchy

Prefer cheapest tool that fits:

1. **`mcp__codebase-rag__search_code`** — first choice for symbols, patterns, "where is X used". Returns ranked chunks, cheapest token-wise.
2. **`Grep`** — only when you already know which file(s) to search in.
3. **`Read`** — only when you have an exact path.

## Gotchas

- **Session numbering** is auto-incremented. If `session start` fails, DB might be locked — check `.tausik/tausik.db-wal`.
- **Session duration limit** — SENAR Rule 9.2. If `compact` status flags warning, surface it prominently and suggest `/end`.
- **MCP self_check** must run in Phase 1 — it's the only signal for stale-module hangs (#77/#79/#80). If `drift_detected=true`, do NOT trust subsequent MCP results in this session; warn the user and use `.tausik/tausik` CLI for verify/task_done until IDE restart.
