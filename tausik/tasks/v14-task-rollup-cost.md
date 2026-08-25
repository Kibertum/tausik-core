---
slug: v14-task-rollup-cost
title: "Агрегат стоимости по task_slug за период"
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
completed_at: "2026-05-01T11:05:01Z"
---

## Goal

Отчёт для метрик/дашборда.

## Acceptance Criteria

1. Запрос или сервис rollup. 2. Пример вывода. 3. Negative: пустой период — пустой отчёт без exception.

## Plan

## Rollback

## Journal

- 2026-05-01T11:04:58Z [implementation] — AC verified: 1. ✓ backend usage_events_cost_rollup_by_task + usage_cost_rollup_by_task. 2. ✓ metrics cost / --cost tabular print. 3. ✓ пустое окно: [] и дружелюбный print в CLI + pytest test_usage_cost_rollup_session_record_without_task_excluded.
