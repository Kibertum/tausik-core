---
slug: v14-status-json-compact
title: "Компактный вывод tausik_status / MCP (опция или версионирование)"
status: done
epic: v14-framework-lean
story: v14-lean-mcp-surface
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "scripts/tausik_utils.py scripts/project_cli.py scripts/project_parser.py agents/claude/mcp/project/handlers.py agents/cursor/mcp/project/handlers.py agents/claude/mcp/project/tools.py agents/cursor/mcp/project/tools.py .claude/mcp/project/ docs/en/cli.md docs/ru/cli.md docs/en/mcp.md docs/ru/mcp.md tests/test_project_mcp.py"
scope_exclude: null
relevant_files:
  - "scripts/project_cli.py"
  - "scripts/project_service.py"
  - "tests/test_hud_cli.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T10:47:17Z"
---

## Goal

Не ломать существующих парсеров без явного флага.

## Acceptance Criteria

1. Флаг или новое поле. 2. docs. 3. Negative: без флага формат прежний.

## Plan

## Rollback

## Journal

- 2026-05-01T10:47:17Z [implementation] — AC verified: 1. ✓ CLI status --compact и MCP tausik_status compact. 2. ✓ EN/RU cli.md + mcp.md. 3. ✓ Без флага/compact=false прежний текст. Зеркала .claude синхронизированы. Tests: AC-3: ✓ tested via tests/test_project_mcp.py.
