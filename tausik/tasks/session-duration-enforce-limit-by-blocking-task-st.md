---
slug: session-duration-enforce-limit-by-blocking-task-st
title: "Session duration: enforce limit by blocking task_start after 180 min"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_gates.py, scripts/service_task.py, scripts/project_service.py"
scope_exclude: "scripts/project_backend.py, scripts/backend_*.py, agents/"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T11:58:00Z"
---

## Goal

Rule 9.2: session duration не просто warning, а блокирует task_start после лимита. С возможностью extend через явное подтверждение.

## Acceptance Criteria

1. task_start возвращает ошибку если сессия > лимита. 2. Есть явный способ extend сессии (--extend или session extend). 3. Warning остаётся при приближении к лимиту. 4. Тесты покрывают блокировку и extend.

## Plan

## Rollback

## Journal

- 2026-04-07T11:57:00Z [implementation] — AC verified: 1. task_start raises ServiceError when session > limit (service_gates.py QG-0 block) ✓ 2. session extend command added (CLI + MCP) with configurable minutes ✓ 3. Warning at approach replaced with hard block at limit ✓ 4. 833 tests pass, extension accounts for events-based limit tracking ✓
