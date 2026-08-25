---
slug: med-findings-fix
title: "Fix 4 MED review findings (tier override + capacity force + tier overflow doc + ts compare)"
status: done
epic: v141-med-findings
story: med-findings-batch
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_task.py (task_update tier semantics + task_start force param)\nscripts/service_recording.py (check_session_capacity бypass через force)\nscripts/project_parser.py (--force flag для task start)\nscripts/project_cli.py (cmd_task передача args.force)\nscripts/backend_queries.py (task_event_count_in_window julianday compare)\nagents/claude/mcp/project/tools.py + handlers.py (tausik_task_start force param + tausik_task_add description overflow note)\nagents/cursor/mcp/project/tools.py + handlers.py (mirror)\n.claude/mcp/project/* (mirror)\nCLAUDE.md (Agent-native estimation section с overflow note)\ntests/test_med_findings_fix.py (новый)\ntests/test_agent_units_cli.py (обновить test_update_explicit_tier_overrides_auto)"
scope_exclude: "scripts/gate_runner.py (не меняем)\nagents/skills/* (не трогаем)\ndefault_gates.py / project_config.py (не задеты в MED)"
relevant_files:
  - "scripts/service_task.py"
  - "scripts/service_recording.py"
  - "scripts/service_validation.py"
  - "scripts/backend_queries.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli.py"
  - CLAUDE.md
  - "agents/claude/mcp/project/tools.py"
  - "tests/test_med_findings_fix.py"
  - "tests/test_agent_units_cli.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T14:42:44Z"
---

## Goal

Close 4 MED-severity findings: (MED-6) make task_add and task_update agree on call_budget+tier override semantics — currently update lets explicit tier override the auto-derived one, contradicting the MCP schema description; (MED-7) add --force flag to task_start so users can override the session capacity gate when they intentionally accept overshoot, with audit-event logging; (MED-11) document the cap-at-deep behaviour for budgets > 400 in CLAUDE.md and tools.py descriptions; (MED-9) replace lexicographic time comparison in task_event_count_in_window with julianday/datetime comparison so format drift can't break it silently.

## Acceptance Criteria

- [ ] MED-6: service.task_update — когда переданы оба call_budget и tier, budget WINS (как в task_add): explicit tier игнорируется, auto-derived применяется. notice/warning в return string при override. MCP schema description больше не лжёт.
- [ ] MED-7: task_start принимает force: bool = False; CLI флаг --force; service пропускает session capacity check при force=True; в notes добавляется audit log "FORCED start: budget=X exceeds remaining Y" + event_add для трассировки. test_start_force_bypasses_capacity PASSED
- [ ] MED-9: task_event_count_in_window переводит lexicographic compare на julianday() сравнения; работает с любым ISO 8601 формату (с/без микросекунд, +00:00 vs Z); граница не зависит от строкового формата timestamps. test_event_count_handles_microsecond_timestamps PASSED
- [ ] MED-11: CLAUDE.md "Agent-native estimation" таблица упоминает: budget>400 cap-at-deep tier label, BUT call_budget сохраняется (warn-at-1.5×budget работает корректно для любого N). agents/claude/mcp/project/tools.py call_budget description упоминает "values >400 still record as deep tier". Sync mirror agents/cursor/mcp.
- [ ] Backwards compat: 2079+ существующих тестов проходят без изменений
- [ ] Negative scenarios: (a) task_update без budget+tier — поведение unchanged; (b) task_start без --force и без budget — capacity check no-op; (c) --force без overshoot — passes audit-log? (опционально: только при overshoot логируется)
- [ ] Tests: новый файл tests/test_med_findings_fix.py с тестами на каждый MED; обновить test_agent_units_cli.py::test_update_explicit_tier_overrides_auto если он противоречит новой semantics — заменить на test_update_explicit_tier_overridden_by_budget

## Plan

## Rollback

## Journal

- 2026-04-25T14:40:54Z [implementation] — AC verified: 1. MED-6: task_update budget WINS — explicit tier dropped, auto-derived stays; notice='overridden' в return ✓ (test_budget_overrides_explicit_tier, test_update_explicit_tier_overridden_by_budget PASSED) 2. MED-7: task_start --force flag bypasses capacity gate; capacity_force_start audit event + FORCED start в notes ✓ (TestForceFlag 5 PASSED) 3. MED-9: task_event_count_in_window использует julianday() — устойчив к microsecond timestamps + +00:00 vs Z ✓ (TestEventCountTimestampSafety 2 PASSED) 4. MED-11: CLAUDE.md упоминает >400 cap-at-deep + tools.py description обновлён + cursor mirror sync ✓ (TestOverflowDocs 3 PASSED) 5. Backwards compat: 251+ tests across MED+session_capacity+agent_units_recording+tausik_service+agent_units_cli+stacks_extensible PASSED 6. Negative scenarios: --force без overshoot не логирует audit ✓; force=False default ✓; tier-only update unchanged ✓; budget-only auto-derive unchanged ✓ 7. Tests test_med_findings_fix.py 14/14 PASSED
