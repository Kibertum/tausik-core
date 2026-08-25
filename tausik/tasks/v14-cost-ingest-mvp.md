---
slug: v14-cost-ingest-mvp
title: "MVP сбор usage: ручной лог или хук-заглушка"
status: done
epic: v14-cost-telemetry
story: v14-cost-ingest
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_metrics_session_usage.py"
  - "agents/claude/mcp/project/tools.py"
  - "agents/claude/mcp/project/handlers.py"
  - "agents/cursor/mcp/project/tools.py"
  - "agents/cursor/mcp/project/handlers.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T11:04:52Z"
---

## Goal

Документированный способ записать usage_events без IDE SDK.

## Acceptance Criteria

1. CLI или MCP draft log usage. 2. docs. 3. Negative: malformed payload возвращает ошибку.

## Plan

## Rollback

## Journal

- 2026-05-01T11:04:13Z [implementation] — AC verified: 1. ✓ CLI metrics log-usage + MCP tausik_usage_event_log (required fields guarded). 2. ✓ docs EN/RU mcp+cli. 3. ✓ Negative: pytest ServiceError; MCP без KeyError при пустых args.
