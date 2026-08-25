---
slug: mcp-gaps
title: "MCP: закрыть gaps — dead-end, explore, audit, gates, skills, incomplete params"
status: done
epic: null
story: null
complexity: complex
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
completed_at: "2026-03-26T15:33:14Z"
---

## Goal

Все CLI-команды доступны через MCP. Агент не падает в CLI bash для основных операций

## Acceptance Criteria

1. MCP tools: frai_dead_end, frai_explore_start/end/current, frai_audit_check/mark. 2. MCP tools: frai_gates_status/enable/disable. 3. MCP tools: frai_skill_list/activate/deactivate. 4. frai_task_add: параметр defect_of. 5. frai_task_done: параметр ac_verified. 6. frai_memory_add: тип dead_end в enum. 7. MCP tools для update-claudemd и fts optimize. 8. Все новые tools в tools.py + handlers.py для claude И cursor.

## Plan

[{"step": "Add all missing MCP tools + fix incomplete params", "done": true}]

## Rollback

## Journal
