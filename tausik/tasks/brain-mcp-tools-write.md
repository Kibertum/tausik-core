---
slug: brain-mcp-tools-write
title: "MCP write-tools: brain_store_decision/pattern/gotcha/cache_web"
status: done
epic: shared-brain
story: brain-mcp-server
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_mcp_write.py (new), agents/claude/mcp/brain/handlers.py (extend), agents/claude/mcp/brain/tools.py (extend), tests/test_brain_mcp_write.py (new)"
scope_exclude: "scripts/brain_scrubbing.py (stable), scripts/brain_notion_client.py (stable), scripts/brain_config.py (stable), .mcp.json / bootstrap/** (wiring task)"
relevant_files:
  - "scripts/brain_mcp_write.py"
  - "agents/claude/mcp/brain/handlers.py"
  - "agents/claude/mcp/brain/tools.py"
  - "tests/test_brain_mcp_write.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T09:01:20Z"
---

## Goal

Four MCP write-tools (brain_store_decision, brain_store_pattern, brain_store_gotcha, brain_cache_web). Each composes Notion property JSON for its category, runs content through scrubbing linter (brain_scrubbing.scrub_with_config), refuses on block-severity issues with formatted guidance. On success: creates the Notion page, mirrors the returned page into the local SQLite via brain_sync.map_page_to_row + upsert (instant-consistency; no need for next pull). Project hash auto-derived from cwd basename with TAUSIK_PROJECT_NAME env override; optional explicit project_name arg overrides both.

## Acceptance Criteria

1) scripts/brain_mcp_write.py exposes build_properties_{decision,web_cache,pattern,gotcha} (pure) and store_record(client, conn, category, fields, cfg, project_name?) that runs scrub → create → local upsert.
2) scrub_inputs(category, fields, cfg) joins text fields and calls brain_scrubbing.scrub_with_config; store_record short-circuits on scrub failure returning {"status": "scrub_blocked", "issues": [...]}.
3) 4 handlers in agents/claude/mcp/brain/handlers.py: handle_brain_store_decision/pattern/gotcha/cache_web + dispatch rows in handle_tool.
4) 4 Tool schemas appended to agents/claude/mcp/brain/tools.py with JSON inputSchema, required primary fields (name + body), optional tags/stack/confidence/severity/etc.
5) Project hash: _resolve_project_name() → explicit arg | os.getenv("TAUSIK_PROJECT_NAME") | os.path.basename(os.getcwd()); compute_project_hash turns it into SHA256[:16].
6) web_cache: Content Hash = SHA256(content)[:16]; auto-computed by store_record.
7) Local mirror invalidation: after successful Notion create, store_record maps returned page JSON through brain_sync.map_page_to_row and calls upsert_page. sync_state.last_pull_at is left alone; next sync still picks up edits via last_edited_time ordering.
8) ≥20 tests in tests/test_brain_mcp_write.py: each of the 4 builders, scrub-blocked returns issues, happy path calls client + upsert, Notion error propagates as warning, content hash determinism, category-specific required-field validation, handler dispatch for each of 4 new tools.
9) mypy + ruff clean; full pytest suite passes; no regressions.
10) Out of scope: scrubbing linter itself (already done as brain-scrubbing), MCP server wiring (brain-mcp-server-wiring), init wizard (brain-init-wizard), additional detector types.

## Plan

[{"step": "Design field \u2194 property mapping per category (mirror brain_sync._map_* + Notion payload shape from references/brain-db-schema.md \u00a73)", "done": true}, {"step": "scripts/brain_mcp_write.py: build_properties_* for 4 categories, compute_content_hash, _resolve_project_name, scrub_inputs, store_record, format_store_result", "done": true}, {"step": "tests/test_brain_mcp_write.py: \u226520 tests \u2014 builders produce correct Notion shape, scrub blocks, happy path, hash determinism, handler dispatch", "done": true}, {"step": "Extend agents/claude/mcp/brain/tools.py with 4 new Tool schemas", "done": true}, {"step": "Extend agents/claude/mcp/brain/handlers.py with 4 new handlers + dispatch entries", "done": true}, {"step": "Run mypy + ruff on new+touched files; full pytest suite", "done": true}, {"step": "Log AC evidence; task done", "done": true}]

## Rollback

## Journal

- 2026-04-23T08:57:59Z [implementation] — AC verified: 1. brain_mcp_write.py with 4 builders + store_record ✓ 2. scrub_inputs short-circuits scrub_blocked ✓ test_store_record_scrub_block_returns_issues 3. 4 handlers added + _handle_store dispatch ✓ test_handler_brain_store_*_happy 4. 4 Tool schemas in tools.py ✓ 5. _resolve_project_name cascade (arg→env→cwd) ✓ test_resolve_project_name_* 6. compute_content_hash auto for web_cache ✓ test_store_record_happy_path_web_cache_autohashes_content 7. store_record mirrors via map_page_to_row+upsert_page ✓ test_store_record_happy_path_decision reads row from mirror 8. 34 tests (≥20) ✓ 9. mypy + ruff clean, 1396 pass ✓ 10. scope held (no scrubbing/notion_client/config changes) ✓
