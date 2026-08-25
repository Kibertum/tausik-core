---
slug: mcp-task-show-hides-the-fields-the-agent-is-judged-by
title: "MCP task_show скрывает поля, по которым агента судят: область записи и план отката"
status: planning
epic: landscape-2026-h2
story: l26-silent-failures-in-shipped-commands
complexity: medium
role: backend
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "harness/claude/mcp/project/*.py"
  - "scripts/*.py"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: null
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
