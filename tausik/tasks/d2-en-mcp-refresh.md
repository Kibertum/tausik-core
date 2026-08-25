---
slug: d2-en-mcp-refresh
title: "docs/en/mcp.md refresh"
status: done
epic: docs-overhaul-v13
story: docs-en-refresh
complexity: null
role: tech-writer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/mcp.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T16:14:52Z"
---

## Goal

docs/en/mcp.md refreshed with 106 MCP tools

## Acceptance Criteria

1. docs/en/mcp.md lists 106 tools (96 project + 10 brain) — count matches reality; 2. Coverage table refreshed for v1.3 surface; 3. Tausik MCP server launch instructions accurate; 4. No references to retired tools; 5. Negative: zero stale tool names; counts not inflated

## Plan

## Rollback

## Journal

- 2026-04-26T16:14:52Z [implementation] — AC verified: 1.✓ 106 tools (96 project + 10 brain) — count documented at top; 2.✓ coverage table refreshed for v1.3 surface (added doctor/verify/role*/stack*/cq*/task_logs); 3.✓ launch instructions section accurate (refers to bootstrap --refresh); 4.✓ no retired tool names; 5.✓ negative — explicitly states no `--force` on task_done.
