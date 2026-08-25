---
slug: v15s-rule7-rootcause-hardgate
title: "[P2] SENAR Rule 7: structured root cause для defect-задач"
status: done
epic: v15-senar-hardening
story: v15s-rules
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/root_cause.py (новый: ROOT_CAUSE_CATEGORIES closed-list, parse_root_cause, has_structured_root_cause, root_cause_metrics(q)). scripts/service_task_done.py (advisory escalating-nudge на отсутствие структуры у defect — keyword-hard остаётся). scripts/project_cli_ops.py (вывод root-cause coverage в cmd_metrics, паттерн review_metrics). docs/ru/agent-contract.md (формат structured root cause). tests/test_root_cause.py."
scope_exclude: "backend_queries.py / backend_crud.py (оба near/over 400 — не трогаем; метрика через root_cause.py + svc.be._q как session-metrics), keyword root-cause hard-gate в service_task_done (остаётся как floor, decision #96)"
relevant_files:
  - "scripts/root_cause.py"
  - "scripts/service_task_done.py"
  - "scripts/project_cli_ops.py"
  - "tests/test_root_cause_structured.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T12:02:22Z"
---

## Goal

Rule 7 (3.5/5, keyword-detection ограничен): задачи с defect_of обязаны иметь структурированный root_cause (category + описание + prevention) при done — hard вместо warning. AC: схема root_cause (closed list категорий); task done блокирует defect без него; метрика root-cause coverage в metrics.

## Acceptance Criteria

1. root_cause.py: closed-list ROOT_CAUSE_CATEGORIES; parse_root_cause(notes) извлекает category+description+prevention; has_structured_root_cause распознаёт структуру. 2. root_cause_metrics(q) считает coverage (% defect-done с структурным root cause), выводится в tausik metrics. 3. service_task_done: defect с keyword-но-без-структуры -> advisory escalating nudge (keyword-hard остаётся floor). 4. Ошибка/boundary: defect без notes / неизвестная категория -> не структурный, без исключения; нет defect-задач -> coverage 0 без деления на ноль. 5. pytest: парсер (валидная/невалидная категория) + coverage + nudge.

## Plan

## Rollback

git revert коммита; удалить root_cause.py + строки вывода/nudge. Keyword hard-gate не затрагивается, откат чистый, без миграций.

## Journal

- 2026-06-13T10:19:02Z [implementation] — Изучил структуру: keyword hard-gate в service_task_done.py:219-246 (остаётся floor, decision #96). Паттерн метрик — review_metrics в backend_crud.py:107 + вывод в project_cli_ops.py cmd_metrics:92-101. nudge API: escalate/reset(conn, invariant, msg). План: новый scripts/root_cause.py (ROOT_CAUSE_CATEGORIES closed-list + parse_root_cause + has_structured_root_cause + root_cause_metrics(q)); advisory nudge в else-ветке (keyword есть, structure нет); coverage в cmd_metrics через svc.be._q.
- 2026-06-13T11:43:14Z [implementation] — AC verified (decision #96, structured без хард-апгрейда): 1. ✓ root_cause.py — ROOT_CAUSE_CATEGORIES (11 closed-list) + parse_root_cause + has_structured_root_cause (tests/test_root_cause_structured.py::TestParseRootCause, 8 тестов вкл. все категории/ru/embedded). 2. ✓ root_cause_metrics(q) coverage через svc.be._q + вывод в cmd_metrics (project_cli_ops.py, паттерн review_metrics); TestRootCauseMetrics::test_coverage_mixed=50%. 3. ✓ service_task_done.py — advisory escalating-nudge в else-ветке (keyword есть, structure нет); keyword hard-gate floor НЕ тронут; TestStructuredNudge. 4. ✓ boundary: unknown category/empty notes → not structured без исключения; нет defect-задач → coverage 0.0 без ZeroDivisionError (test_no_defect_tasks_no_zero_division). 5. ✓ pytest 12/12 + 73 в затронутой области. ruff clean; service_task_done.py=393, project_cli_ops.py=397 (<400). backend_queries/crud НЕ тронуты. Knowledge: формат structured root cause задокументирован в docs/ru/agent-contract.md (canonical), отдельной memory не требуется.
- 2026-06-13T11:59:10Z [implementation] — AC verified via CLI repro
- 2026-06-13T12:02:22Z [implementation] — AC verified (repro)
