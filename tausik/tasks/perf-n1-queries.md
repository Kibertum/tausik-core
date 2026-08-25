---
slug: perf-n1-queries
title: "Оптимизировать N+1: metrics, roadmap, team_status, task_next"
status: done
epic: polish
story: perf
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_queries.py"
  - "scripts/service_task.py"
  - "scripts/project_backend.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T19:41:58Z"
---

## Goal

get_metrics: 8→3-4 round-trips (combined COUNT queries). get_roadmap_data: фильтр done в SQL. team_status/task_next: фильтр в SQL, не в Python.

## Acceptance Criteria

1. get_metrics: <= 4 SQL round-trips (было 8). 2. get_roadmap_data: фильтр done в SQL (WHERE status != 'done' когда include_done=False). 3. team_status: передаёт status filter в task_list. 4. task_next: SQL с ORDER BY score DESC LIMIT 1. 5. Ошибка если get_metrics делает > 4 отдельных cursor.execute.

## Plan

[{"step": "get_metrics: \u043e\u0431\u044a\u0435\u0434\u0438\u043d\u0438\u0442\u044c COUNT queries \u0447\u0435\u0440\u0435\u0437 CASE WHEN", "done": true}, {"step": "get_roadmap_data: \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c WHERE status != 'done' \u043f\u0440\u0438 include_done=False", "done": true}, {"step": "team_status: \u043f\u0435\u0440\u0435\u0434\u0430\u0442\u044c status filter \u0432 self.be.task_list", "done": true}, {"step": "task_next: \u043d\u043e\u0432\u044b\u0439 backend \u043c\u0435\u0442\u043e\u0434 \u0441 ORDER BY score DESC LIMIT 1", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c \u0442\u0435\u0441\u0442\u044b", "done": true}]

## Rollback

## Journal

- 2026-04-05T19:41:49Z [implementation] — AC verified: 1. get_metrics 8→4 queries (combined SELECT) ✓ 2. get_roadmap_data WHERE status!='done' ✓ 3. team_status передаёт status filter ✓ 4. task_next: task_next_candidate() SQL LIMIT 1 ✓ 5. 738/738 тестов ✓
