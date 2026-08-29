---
slug: the-breaking-flip-announced-to-an-external-author-has-no-task
title: "Слом умолчания хуков объявлен внешнему автору как входящий в 1.9, но задачи на него нет и код по-прежнему fail-open"
status: planning
epic: null
story: null
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 80
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР СЕССИИ #189. В комментарии к PR #5 (2026-08-04) владелец публично объявил, что PR несёт ЛОМАЮЩЕЕ изменение и что именно поэтому он едет в 1.9, а не в 1.8.1: «task_gate becomes fail-secure by default and TAUSIK_HOOK_FAIL_SECURE=1 is replaced by its inverse TAUSIK_HOOK_FAIL_OPEN=1». Там же прямым текстом: «We also agree with the default flip on the merits. A guard that cannot evaluate should refuse, not wave the edit through — the project already argues this for QG-0 and QG-2, and task_gate was the exception that contradicted it.»

СОСТОЯНИЕ КОДА НА СЕГОДНЯ, ПРОВЕРЕНО ЧТЕНИЕМ:
  scripts/hooks/task_gate.py:11-16 — докстринга по-прежнему объявляет fail-open УМОЛЧАНИЕМ, а fail-secure — opt-in по флагу;
  task_gate.py:131, scope_write_gate.py:187, bash_write_gate.py:111 — все три читают os.environ.get("TAUSIK_HOOK_FAIL_SECURE"); hook_supervision.py:216 ссылается на него же;
  TAUSIK_HOOK_FAIL_OPEN не встречается в дереве НИ РАЗУ;
  всего 15 вхождений старого имени в scripts/ и docs/.
То есть ни поведение, ни имя переменной не изменены.

ЗАДАЧИ НА ЭТО НЕТ. Поиск по всем задачам даёт r14-task-gate-secure — она статуса done и относится к выпуску 1.4: именно она и ВВЕЛА нынешнюю схему «fail-open по умолчанию, fail-secure по флагу». Задача port-external-pr5-hook-coverage перечисляет в AC2 шесть переносимых правок (якорение матчеров, MCP-редакторы, MultiEdit, NotebookEdit, единый источник имён, поле пути в payload) — слома умолчания среди них НЕТ. Дыра в планировании, а не отложенное решение.

ПОЧЕМУ ЭТО ДОРОЖЕ ОБЫЧНОЙ ПРОПУЩЕННОЙ ЗАДАЧИ. Обещание дано ВНЕШНЕМУ автору публично и служило обоснованием, почему его вклад ждёт целого релиза вместо патча. Если 1.9 выйдет без слома, то и объяснение задержки окажется неверным задним числом.

СМЕЖНОЕ, УЧЕСТЬ В ТОМ ЖЕ ЗАХОДЕ: в release notes 1.9 уже не попали восемь изменений поведения (пять из волн 1-2, tausik audit evidence, импортное ребро и второй детектор храповика), и рядом висит blocked-задача release-18-breaking-change-notes ровно про этот класс упущения. Слом умолчания хуков — девятое, и оно ломающее, то есть требует не строки в CHANGELOG, а объявления по всем местам, где 1.8 перечисляла свои шесть ломающих (по замеру самой 1.8 — семь мест плюс закрепляющий тест).

ДО КОДА ЗАМЕРИТЬ: (1) сколько установок читают TAUSIK_HOOK_FAIL_SECURE сегодня — переменную могли задать потребители, и переименование сломает их молча; (2) что делает каждый из четырёх хуков при недоступной БД сейчас и что должен делать после; (3) не окажется ли fail-secure по умолчанию причиной кирпича у потребителя с битой БД — ровно тот довод, которым умолчание обосновано в докстринге 1.4 («tausik doctor issues never brick a project»), и он не опровергнут, а лишь перевешен.

## Acceptance Criteria

## Plan

## Rollback

## Journal
