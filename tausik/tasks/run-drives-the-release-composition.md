---
slug: run-drives-the-release-composition
title: "Скилл /run ведёт состав релиза из БД и закрывает задачи в одном ходу"
status: planning
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 90
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

ТРЕТЬЯ ИЗ ПЯТИ ЗАДАЧ АВТОНОМНОСТИ — ядро драйвера (ревью смены #277).

НАЙДЕНО РЕВЬЮ: механизм автономности СУЩЕСТВУЕТ, но в kiberza, а не в core. Там скилл /run (214 строк) разбирает plan.md со слагами и проходит task → реализация → task done последовательно В ОДНОМ ХОДУ, с hard-stop на первом отказе и одним сводным handoff на батч. В core такого скилла нет вовсе: список — checkpoint, commit, debug, end, explore, i-have-adhd, interview, plan, reason, review, ship, start, task, test. То есть автономность у core записана ИНСТРУКЦИЕЙ в CLAUDE.md, а инструкция без механизма — ровно то, против чего проект строит храповики.

ЧТО У KIBERZA УЖЕ ХОРОШО и переносится: контракт разбора плана, hard-stop без авто-повторов, один сводный handoff вместо одного на задачу, прямой запрет применять режим к задачам, требующим суждения владельца.

ЧТО СДЕЛАТЬ ЛУЧШЕ, три отличия. Первое: источник истины — СОСТАВ РЕЛИЗА В БД, а не файл plan.md; у core уже есть `task next` с порядком «релиз первым, затем объявленный порядок», и дублировать его файлом значит заводить вторую правду. Второе: предел не «5 задач», а «пока состав не пуст ИЛИ не исчерпан контекст» — иначе это батч, а не автономность. Третье: перед каждой задачей сверяться с планом заново, потому что состав мог измениться закрытием предыдущей.

ЗАВИСИМОСТИ ЖЁСТКИЕ: без бюджета журнала (journal-and-changelog-have-a-budget) прогон задохнётся на контексте — замер смены #277 даёт 7407 символов журнала на задачу, то есть 20 задач это 150 тысяч символов. Без жёсткого потолка вызовов (call-budget-is-armed-in-autonomous-mode) сожжёт смену на одной задаче. Делать третьей.

## Acceptance Criteria

## Plan

## Rollback

## Journal
