---
slug: fix-truly-all
title: "Fix truly ALL remaining: root cause, MCP tests, type hints, time_limit bounds"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-26T16:20:18Z"
---

## Goal

Закрыть 4 пропущенных finding: Rule 7 root cause, MCP handler tests, backend_graph Protocol, exploration time_limit validation

## Acceptance Criteria

1. task_done для defect tasks предупреждает если нет root cause в notes. 2. Минимум 5 handler-level MCP тестов (dead_end, gates_status, explore, skill_list, fts_optimize). 3. backend_graph.py без type:ignore (Protocol или TYPE_CHECKING). 4. exploration time_limit clamped 1-480. 5. Тесты проходят.

## Plan

[{"step": "Fix all 4 missed findings", "done": true}]

## Rollback

## Journal
