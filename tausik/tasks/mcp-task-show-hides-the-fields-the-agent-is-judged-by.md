---
slug: mcp-task-show-hides-the-fields-the-agent-is-judged-by
title: "MCP task_show скрывает поля, по которым агента судят: область записи и план отката"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: backend
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/task_detail_fields.py"
  - "scripts/project_cli_task.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "tests/test_mcp_task_show_fields.py"
scope_paths:
  - "harness/claude/mcp/project/*.py"
  - "scripts/*.py"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-23T23:51:53Z"
---

## Goal

tausik_task_show по MCP показывает те же поля задачи, что и CLI — в первую очередь scope_paths и rollback_plan, по которым агента судят гейты. Перечень полей не дублируется в двух местах, иначе он разойдётся снова.

## Acceptance Criteria

AC1. tausik_task_show возвращает scope_paths и rollback_plan, когда они заполнены. Сегодня обработчик перечисляет ровно шесть полей (role, stack, complexity, goal, notes, acceptance_criteria) плюс план шагов, а CLI показывает сверх этого story_slug, epic_slug, scope_paths, scope_tools, rollback_plan, started_at, attempts.
AC2. ПОЧЕМУ ЭТО НЕ КОСМЕТИКА: scope_paths — это ACL, которым хук scope_write_gate ОТКАЗЫВАЕТ в записи, а rollback_plan — требование SENAR Rule 6. Агент, работающий по правилу MCP-first, упирается в ограничение, которого ему не показали, и узнаёт о нём только из текста отказа.
AC3. Перечень полей живёт в ОДНОМ месте, общем для CLI и MCP. Вторая копия перечня — тот же дефект, что mcp-update-claudemd-erases-the-memory-tail, только отложенный.
AC4. НЕГАТИВНЫЙ СЦЕНАРИЙ: тест обязан СНАЧАЛА ПОКРАСНЕТЬ на текущем обработчике. Он заводит задачу со scope_paths и rollback_plan, зовёт tausik_task_show и требует оба поля в выводе.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: пустые поля НЕ печатаются пустыми строками — задача без scope_paths выводится ровно как сегодня, без лишних заголовков.
AC6. Объём вывода назван числом: задача обязана сравнить длину ответа до и после и подтвердить, что рост укладывается в бюджет токенов MCP-поверхности (у проекта есть храповик стоимости MCP — test_mcp_tool_token_cost).

## Plan

## Rollback

git revert коммита: обработчик возвращается к прежнему перечню полей

## Journal

- 2026-09-23T23:51:18Z [implementation] — Root cause: the MCP handler _handle_task_show kept its own six-field tuple next to the CLI's twenty-six in _print_task_detail; nothing tied the two lists together.
- 2026-09-23T23:51:19Z [implementation] — AC1: ✓ tests/test_mcp_task_show_fields.py::test_the_scope_acl_and_the_rollback_plan_are_shown — tausik_task_show now prints scope_paths and rollback_plan (and every other field the CLI prints) when set.
- 2026-09-23T23:51:19Z [implementation] — AC2: ✓ review — the reason is stated in the new module's docstring and CHANGELOG: scope_paths is the ACL scope_write_gate refuses by, rollback_plan is SENAR Rule 6.
- 2026-09-23T23:51:19Z [implementation] — AC3: ✓ tests/test_mcp_task_show_fields.py::test_cli_and_mcp_read_one_list — scripts/task_detail_fields.py holds TASK_DETAIL_FIELDS and detail_lines; the CLI and the MCP handler both call detail_lines and neither keeps a copy of the list.
- 2026-09-23T23:51:20Z [implementation] — AC4: ✓ tests/test_mcp_task_show_fields.py::test_the_scope_acl_and_the_rollback_plan_are_shown — negative, written first and RED on the six-field handler (output was 'Task/Title/Status/Relevant memory' only), green after.
- 2026-09-23T23:51:20Z [implementation] — AC5: ✓ tests/test_mcp_task_show_fields.py::test_empty_fields_print_nothing — negative, a task without scope_paths/rollback_plan prints no such header and no line ending in a bare colon.
- 2026-09-23T23:51:20Z [implementation] — AC6: ✓ measurement — tausik_task_show over three real tasks: 20430 chars before, 21949 after (+7.4%, ~500 chars/~125 tokens per task); the MCP token ratchet counts tool SCHEMAS, which did not change; 792 related tests pass.
