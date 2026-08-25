---
slug: brain-mcp-tools-read
title: "MCP read-tools: brain_search, brain_get"
status: done
epic: shared-brain
story: brain-mcp-server
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_mcp_read.py (new), agents/claude/mcp/brain/tools.py (new), agents/claude/mcp/brain/handlers.py (new), tests/test_brain_mcp_read.py (new)"
scope_exclude: "scripts/brain_search.py (stable), scripts/brain_notion_client.py (stable), .mcp.json (wiring task), bootstrap/** (wiring task), any write-side brain_store_* (write-tools task)"
relevant_files:
  - "scripts/brain_mcp_read.py"
  - "agents/claude/mcp/brain/tools.py"
  - "agents/claude/mcp/brain/handlers.py"
  - "tests/test_brain_mcp_read.py"
  - "tests/test_brain_mcp_handlers.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T08:33:16Z"
---

## Goal

Two read-only MCP tools (brain_search, brain_get) backed by local FTS5 mirror with Notion API fallback. brain_search: local bm25 first; if local is empty OR stale, hit Notion databases.query and merge. brain_get: local lookup first; fallback to Notion pages.retrieve. Responses normalized to markdown (title, category badge, body, metadata). Both tools gracefully degrade: missing brain config → clear error; Notion network failure → returns local-only result with warning. Handlers tested directly; separate brain MCP server/wiring is scoped out (see brain-mcp-server-wiring).

## Acceptance Criteria

1) brain_search(query, category?, limit=10, use_notion_fallback=true) returns markdown list of ranked matches; when local has <limit hits AND fallback enabled AND brain configured → queries each Notion category DB, merges results, dedup by notion_page_id; empty/unconfigured → explanatory message.
2) brain_get(id, category) returns full record as markdown; local first, Notion pages.retrieve fallback; not-found → clear error.
3) Markdown format: H2 title, category badge, body/snippet, footer with id+project_hash+timestamps. Helper `_format_record(category, row)` reused across both tools.
4) Notion fallback never hangs the tool: 5s connect timeout, single retry, on failure return local results + warning footer.
5) New files: agents/claude/mcp/brain/tools.py (JSON schemas), agents/claude/mcp/brain/handlers.py (dispatch + handle_brain_search/handle_brain_get). No server.py yet.
6) New module scripts/brain_mcp_read.py with pure helpers (search_with_fallback, get_with_fallback, format_record) — testable without MCP runtime.
7) ≥15 tests in tests/test_brain_mcp_read.py: local-only, fallback-triggered, fallback-network-error, empty-query, bad-category, unknown-id, markdown format assertions.
8) mypy + ruff clean on new files; existing 1294 tests still pass.
9) Out of scope: brain MCP server wiring (separate task), write-tools (separate task), Notion auth bootstrap (brain-init-wizard).

## Plan

[{"step": "Design markdown format helper _format_record \u2014 study Notion page shape (schema) for each of 4 categories to pick footer fields", "done": true}, {"step": "Create scripts/brain_mcp_read.py: search_with_fallback, get_with_fallback, _format_record, _query_notion_category, _retrieve_notion_page. Pure functions, inject db and client deps", "done": true}, {"step": "Write tests/test_brain_mcp_read.py (\u226515): local-only, fallback merges remote, network error returns local+warning, dedup by notion_page_id, missing config, unknown category, markdown shape", "done": true}, {"step": "Create agents/claude/mcp/brain/tools.py with JSON schemas for brain_search + brain_get", "done": true}, {"step": "Create agents/claude/mcp/brain/handlers.py \u2014 dispatch by name, construct client from config, call helpers, return markdown", "done": true}, {"step": "Run mypy + ruff on new files; run pytest full suite", "done": true}, {"step": "Log AC verification evidence: each AC # \u2192 test/assertion mapping", "done": true}, {"step": "task done --ac-verified", "done": true}]

## Rollback

## Journal

- 2026-04-23T08:17:11Z [implementation] — Step 1: studying brain_schema tables + brain_sync mappers to design _format_record helper
- 2026-04-23T08:22:22Z [implementation] — Steps 1-5 done. Created scripts/brain_mcp_read.py (223 lines), agents/claude/mcp/brain/tools.py (54), handlers.py (105). 38 tests green (28 read + 10 handlers). Mypy + ruff clean on new files. Running full suite now.
- 2026-04-23T08:29:46Z [implementation] — AC verification evidence: AC1 brain_search: test_search_fallback_triggers_when_local_short, test_search_category_filter_passes_through_local, test_search_fallback_disabled_flag AC2 brain_get: test_get_fallback_to_notion_on_local_miss, test_get_local_hit_no_fallback, test_get_miss_no_client AC3 markdown shape: test_format_record_basic_shape, test_format_record_web_cache_shows_url, test_format_record_pattern_shows_confidence_badge, test_format_record_gotcha_shows_severity_and_evidence AC4 network failure → local+warning: test_search_fallback_network_error_returns_local_with_warning, test_get_notion_error_returns_warning; handlers._build_client uses timeout=5.0 max_retries=1 AC5 new files: agents/claude/mcp/brain/tools.py (67), handlers.py (116). No server.py (out of scope). AC6 pure helpers module: scripts/brain_mcp_read.py (300 lines) — search_with_fallback, get_with_fallback, format_record, search_notion, all testable without MCP runtime AC7 test count: 28 in test_brain_mcp_read.py + 10 in test_brain_mcp_handlers.py = 38, ≥15 ✓ AC8 mypy: Success: no issues found in 3 source files. Ruff: All checks passed. pytest: 1332 passed, 2 skipped (prev 1294 + 38 new, zero regressions) AC9 scope held: no .mcp.json edit, no server.py, no write-tools, no bootstrap changes Dedup test used same notion_page_id on local + remote; local row wins (test_search_fallback_dedup_prefers_local). Dash normalization covered by test_search_dash_normalization_in_db_ids. Cyrillic preserved by test_format_record_preserves_cyrillic.
- 2026-04-23T08:29:53Z [implementation] — AC verified: 1. brain_search with fallback ✓ 2. brain_get with fallback ✓ 3. markdown shape ✓ 4. fallback never hangs / warning on net fail ✓ 5. tools.py + handlers.py created, no server.py ✓ 6. pure helpers in brain_mcp_read.py ✓ 7. 38 tests (≥15) ✓ 8. mypy + ruff clean, 1332 pass ✓ 9. scope held (no wiring, no write tools) ✓
