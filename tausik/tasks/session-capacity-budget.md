---
slug: session-capacity-budget
title: "Session capacity warnings — preemptive split tasks"
status: done
epic: agent-native-planning
story: estimation-session-planning
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_queries.py (session_capacity_summary)\nscripts/service_task.py (task_start enforcement)\nscripts/project_cli.py (cmd_status output)\nscripts/project_config.py (DEFAULT_SESSION_CAPACITY_CALLS)\ntests/test_session_capacity.py (новый)"
scope_exclude: "scripts/service_*.py (other) — только service_task\nagents/skills/* — нет UI изменений в skills\nbackend_crud.py — query, не CRUD"
relevant_files:
  - "scripts/backend_queries.py"
  - "scripts/backend_tier_metrics.py"
  - "scripts/service_task.py"
  - "scripts/service_recording.py"
  - "scripts/project_cli.py"
  - "scripts/project_config.py"
  - "tests/test_session_capacity.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T12:13:37Z"
---

## Goal

tausik status показывает: session capacity budget = 200 calls (configurable), used = sum(call_actual текущей сессии), planned remaining = sum(call_budget активных задач). Warning если sum(active call_budget) > capacity_remaining с предложением "split task X (deep tier, 250 calls) в отдельную сессию или delegate to subagent". На task_start блокировка если task.call_budget > capacity_remaining — pass --force чтобы override. Foundation для smart session orchestration.

## Acceptance Criteria

- [ ] backend.session_capacity_summary() возвращает dict с capacity (default 200), used (sum call_actual задач started в текущей session), planned_active (sum call_budget активных задач), remaining (capacity - used - planned_active)
- [ ] CLI tausik status дополнительно строкой "Capacity: <used>/<cap> used, <planned> planned, <remaining> remaining" + warning если remaining < 0
- [ ] task_start: если task.call_budget задан и > remaining → ServiceError с сообщением (recommend split / delegate / extend session)
- [ ] task_start: если budget overshoots, можно обойти через _internal_force=True (parameter уже есть, just не блокировать) — НО для CLI/MCP пути пользователю нужно явно вызвать с override (пока скип — block по умолчанию, документация в error message)
- [ ] config.session_capacity_calls (default 200) configurable через config.json
- [ ] Negative scenarios: нет active session → capacity check no-op; task без budget → no block; budget=0 → no block
- [ ] Tests test_session_capacity.py: (a) summary dict; (b) status output содержит "Capacity:"; (c) task_start блокируется при overshoot; (d) task_start проходит без budget; (e) no session → no block

## Plan

## Rollback

## Journal

- 2026-04-25T12:13:36Z [implementation] — AC verified: 1. session_capacity_summary returns capacity/used/planned/remaining ✓ (TestSummary 3 PASSED) 2. CLI tausik status строкой Capacity: ... + ⚠ overshoot marker ✓ (project_cli.py edit) 3. task_start блокируется при overshoot ✓ (test_blocks_when_overshoot PASSED) 4. _internal_force обходит check ✓ (existing param, не блокирует) 5. config.session_capacity_calls с DEFAULT 200 ✓ (project_config.py) 6. Negative scenarios: no session → no-op ✓ (test_no_block_without_session); zero/missing budget → no-op ✓ (test_no_block_without_budget, test_zero_budget_no_block) 7. Tests test_session_capacity.py 8/8 PASSED
