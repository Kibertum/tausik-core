---
slug: agent-units-recording
title: "Recording call_actual через events count на task_done"
status: done
epic: agent-native-planning
story: estimation-foundation
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_queries.py (event_count_in_window)\nscripts/service_task.py (task_done модификация)\nscripts/hooks/task_call_counter.py (новый файл)\nbootstrap/bootstrap_generate.py (PostToolUse registration)\n.claude/settings.json (mirror updated config)\ntests/test_agent_units_recording.py (новый файл)"
scope_exclude: "scripts/project_cli*.py (CLI флаги — отдельная задача agent-units-cli-flags)\nscripts/backend_crud.py (helpers уже добавлены в agent-units-schema)\nscripts/backend_schema.py / backend_migrations.py (schema готова)\nagents/skills/plan/ (отдельная задача plan-skill-agent-aware)</scope_exclude>\n</invoke>\n<invoke name=\"mcp__tausik-project__tausik_task_start\">\n<parameter name=\"slug\">agent-units-recording"
relevant_files:
  - "scripts/backend_queries.py"
  - "scripts/service_task.py"
  - "scripts/service_recording.py"
  - "scripts/hooks/task_call_counter.py"
  - "bootstrap/bootstrap_generate.py"
  - ".claude/settings.json"
  - "tests/test_agent_units_recording.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T11:54:21Z"
---

## Goal

На task_done автоматически derive call_actual = count(events) WHERE entity='task' AND entity_id=slug AND created_at BETWEEN task.started_at AND task.completed_at. Также захватывать non-event tool calls через session-tracking hook (новый PostToolUse hook, increments per-task counter в meta table). Записывать в tasks.call_actual. Если task_actual >> task_budget → log warning для будущей calibration.

## Acceptance Criteria

- [ ] Backend query task_event_count_in_window(slug) возвращает count(events) WHERE entity_type='task' AND entity_id=slug AND created_at BETWEEN task.started_at AND task.completed_at; обрабатывает NULL started_at/completed_at (возвращает 0)
- [ ] Новый PostToolUse hook scripts/hooks/task_call_counter.py: ищет единственную active task (status='active'), при наличии инкрементирует meta['tool_calls:<slug>'] (через meta_increment); no-op при отсутствии active task; gracefully игнорирует ошибки (DB locked, нет .tausik/, etc.) — не блокирует tool call
- [ ] task_done в service_task.py: вычисляет actual = events_count + int(meta_get('tool_calls:<slug>') or 0); вызывает be.task_set_call_actual(slug, actual) внутри транзакции task_done; очищает meta key tool_calls:<slug>
- [ ] Budget warning: если task.call_budget задан и actual > 1.5*budget → задача завершается, но в notes пишется WARNING + возвращается строка с предупреждением в task_done output
- [ ] Bootstrap registration: bootstrap_generate.py добавляет task_call_counter.py в PostToolUse список (matcher = "*" или explicit allow-list — выбрать tighter чтобы не давить на каждый Write/Edit/Read; решение: matcher без ограничений, runtime сам решает по active task)
- [ ] .claude/settings.json sync: либо регенерируется из bootstrap_generate, либо обновляется вручную параллельно
- [ ] Tests tests/test_agent_units_recording.py: (a) event_count_in_window с разными started_at/completed_at; (b) hook script — mock active task + meta_increment вызывается; (c) task_done пишет call_actual = events + meta counter и очищает meta; (d) budget warning при actual > 1.5*budget; (e) graceful no-op без active task; (f) backwards-compat — task без budget не получает warning
- [ ] Negative scenario: task без started_at (например marked done через какой-то fast path) не должен ломать task_done — count=0, call_actual=0 если meta пуст

## Plan

## Rollback

## Journal

- 2026-04-25T11:53:29Z [implementation] — AC verified: 1. task_event_count_in_window OK ✓ (test_zero_when_no_started_at, test_counts_events_in_window, test_excludes_other_tasks, test_returns_zero_for_unknown_task PASSED) 2. PostToolUse hook task_call_counter.py: ищет single active, инкрементирует meta, no-op без DB ✓ (4 hook tests PASSED, включая TAUSIK_SKIP_HOOKS=1 опцию) 3. task_done пишет call_actual = events + meta + clears meta ✓ (test_writes_call_actual_from_events, test_includes_meta_counter, test_clears_meta_counter_after_done PASSED) 4. Budget warning при actual > 1.5*budget ✓ (test_budget_warning_when_exceeded PASSED, test_no_warning_within_budget + test_no_warning_without_budget PASSED) 5. Bootstrap registration: bootstrap_generate.py + .claude/settings.json mirror добавили task_call_counter.py к PostToolUse ✓ 6. .claude/settings.json sync ✓ (manual mirror) 7. Tests tests/test_agent_units_recording.py 15/15 PASSED ✓ 8. Negative scenario: task без started_at returns 0 ✓ (test_zero_when_no_started_at PASSED), corrupt meta value не падает ✓ (test_corrupt_meta_value_is_tolerated PASSED) Smoke regression: test_tausik_service + test_tausik_backend + test_e2e_workflow + test_qg2_gates + test_qg0_dimensions + test_hooks 172/172 PASSED.
