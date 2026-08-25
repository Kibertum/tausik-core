---
slug: v14b-defect-task-list-status-csv-schema
title: "MCP tausik_task_list: убрать enum-ограничение со status, чтобы CSV-фильтр работал"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "agents/claude/mcp/project/tools.py, agents/cursor/mcp/project/tools.py, tests/test_mcp_integration.py"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-04T12:17:10Z"
---

## Goal

tausik_task_list MCP-tool принимает comma-separated status (например 'active,blocked,planning') без validation error — соответствует описанию поля и фактическому поведению backend.task_list (splits на CSV → SQL IN). Фикс: заменить enum на pattern либо удалить enum в schema (claude+cursor), пересобрать bootstrap'ом, добавить MCP-integration тест.

## Acceptance Criteria

1. Вызов `tausik_task_list status="active,blocked,planning"` через MCP не возвращает Input validation error и возвращает корректный список задач (объединение трёх статусов).
2. Schema property `status` в `agents/claude/mcp/project/tools.py` и `agents/cursor/mcp/project/tools.py` НЕ содержит `enum` (либо вместо него стоит `pattern` с regex, валидирующий CSV из перечисленных статусов).
3. Description поля `status` явно перечисляет допустимые значения (planning|active|blocked|review|done), чтобы агент не угадывал.
4. Bootstrap пересобран: `agents/claude/mcp/project/tools.py` ↔ `.claude/mcp/project/tools.py` идентичны (cursor — тоже).
5. В `tests/test_mcp_integration.py` добавлен тест: вызов handler с `status="active,done"` возвращает задачи обоих статусов (по уже существующему backend.task_list CSV-разбору).
6. `pytest tests/test_mcp_integration.py` зелёный; mypy чистый по затронутым файлам.

## Plan

## Rollback

## Journal

- 2026-05-04T12:13:31Z [implementation] — Patched tools.py in both claude+cursor: enum → pattern regex (CSV-aware). Description rewritten to be explicit about CSV format.
- 2026-05-04T12:14:07Z [implementation] — Added 2 tests in TestMCPNewToolHandlers: csv_status (handler-level w/ epic+story+4 tasks) + csv_status_schema_pattern (validates schema has pattern not enum, regex matches/rejects expected inputs).
- 2026-05-04T12:16:38Z [implementation] — AC verified: 1. ✓ tausik_task_list status="active,blocked" handler-test passes — returns both, excludes others (test_task_list_csv_status, tests/test_mcp_integration.py) 2. ✓ Schema uses pattern (not enum): test_task_list_csv_status_schema_pattern asserts no 'enum', presence of 'pattern', regex matches single + CSV combos and rejects bogus values (tests/test_mcp_integration.py) 3. ✓ Description rewritten: "Filter by status. Single value or comma-separated list. Allowed: planning, active, blocked, review, done. Examples: 'active' or 'active,blocked,planning'" (agents/{claude,cursor}/mcp/project/tools.py:70) 4. ✓ Bootstrap rerun for all IDE; cross-IDE parity test_claude_cursor_files_identical green; .claude/mcp/project/tools.py mirror has the fix (verified via Grep line 70-71) 5. ✓ Test added in TestMCPNewToolHandlers; both new tests pass 6. ✓ pytest tests/test_mcp_integration.py -m "" → 17/17 passed; mypy on agents/{claude,cursor}/mcp/project/tools.py → "no issues found"
- 2026-05-04T12:16:53Z [implementation] — AC verified: 1. ✓ tausik_task_list status="active,blocked" handler-test passes (test_task_list_csv_status) 2. ✓ Schema uses pattern not enum (test_task_list_csv_status_schema_pattern) 3. ✓ Description explicit (agents/{claude,cursor}/mcp/project/tools.py:70) 4. ✓ Bootstrap rerun, cross-IDE parity green, .claude/mcp/project/tools.py mirror updated 5. ✓ pytest tests/test_mcp_integration.py -m "" → 17/17 passed 6. ✓ mypy agents/{claude,cursor}/mcp/project/tools.py → no issues found
