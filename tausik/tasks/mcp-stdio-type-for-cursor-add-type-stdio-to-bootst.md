---
slug: mcp-stdio-type-for-cursor-add-type-stdio-to-bootst
title: "MCP stdio type for Cursor: add type:stdio to bootstrap-generated .mcp.json and .cursor/mcp.json so Cursor connects TAUSIK servers"
status: done
epic: null
story: null
complexity: null
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_bootstrap_generate_mcp.py"
  - "tests/test_bootstrap_qwen.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_qwen.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T22:26:17Z"
---

## Goal

Bootstrap MCP configs declare stdio transport for Cursor/VS Code hosts

## Acceptance Criteria

Managed TAUSIK servers include type:stdio; pytest bootstrap tests green; .mcp.json regenerated; user-added servers preserved; при отсутствии mcp/brain/server.py tausik-brain не попадает в конфиг (регрессия).

## Plan

## Rollback

## Journal

- 2026-05-07T22:25:16Z [planning] — bootstrap_generate: _stdio_mcp_server + type stdio; bootstrap_qwen parity; tests; regenerated .mcp.json
- 2026-05-07T22:26:12Z [implementation] — AC verified: 1. managed servers have type stdio in bootstrap_generate + regenerated json 2. pytest tests/test_bootstrap_generate_mcp.py tests/test_bootstrap_qwen.py PASS 3. verify --task PASS pytest 4. brain skip path unchanged (test_skips_brain_when_server_missing)
