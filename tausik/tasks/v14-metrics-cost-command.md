---
slug: v14-metrics-cost-command
title: "Команда tausik metrics --cost или эквивалент"
status: done
epic: v14-cost-telemetry
story: v14-cost-dashboard
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
completed_at: "2026-05-01T11:05:09Z"
---

## Goal

Документировано в cli.md.

## Acceptance Criteria

1. Флаг/подкоманда. 2. docs EN/RU. 3. Negative: нет данных — понятное сообщение без traceback.

## Plan

## Rollback

## Journal

- 2026-05-01T11:05:07Z [implementation] — AC verified: 1. ✓ metrics cost + метрики --cost. 2. ✓ cli.md EN/RU. 3. ✓ Negative: пустые данные — print без исключений ( см. cmd_metrics helper _print_usage_cost_rollup ).
