---
slug: adapt-category-list-lives-in-three-literal-copies
title: "Закрытый список категорий находок ADAPT лежит в трёх литеральных копиях плюс перечислением в прозе MCP"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 110
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on:
  - adapt-finding-categories-count-is-written-not-derived
completed_at: null
---

## Goal

НАЙДЕНО ИНВЕНТАРЁМ В СМЕНЕ #201 ПРИ РАБОТЕ НАД adapt-finding-categories-count-is-written-not-derived, ЗАМЕРЕНО ЧТЕНИЕМ ИСХОДНИКОВ, НЕ ПРЕДПОЛОЖЕНО. Заведено ОТДЕЛЬНО СОЗНАТЕЛЬНО, а не приклеено к задаче про счёт: это дефект ДРУГОГО КЛАССА (второй литеральный список против написанного числа) и по объёму равен всей spec-closed-list-is-nine-while-the-standard-has-eleven, которая в #200 закрылась с отметкой COMPLEXITY UNDERSTATED и call_actual=110 против budget=60. Слипание повторило бы ту ошибку буквально.

ЗАМЕР. Закрытый перечень категорий обратных находок (§7.4.4, семь значений) существует в ЧЕТЫРЁХ независимых представлениях плюс схема:
1. scripts/service_adapts.py:28 FINDING_CATEGORIES — кортеж, де-факто источник;
2. scripts/renar_clause_reactive_adapt.py:43 BACKWARD_FINDING_CATEGORIES — СВОЙ кортеж с теми же семью строками, объявленный заново, а не импортированный. Введён в #200 задачей про §13.3.3, то есть копия сделана НЕДЕЛЮ НАЗАД и прошла ревью;
3. harness/claude/mcp/project/tools_adapt.py:11 _FINDING_CATEGORIES — список для enum схемы инструмента MCP;
4. harness/claude/mcp/project/tools_adapt.py:65 — те же семь имён ЕЩЁ РАЗ, перечисленные ПРОЗОЙ внутри description инструмента: «(contradiction/gap/hidden-assumption/feasibility/regulatory/terminology/scope)». Это представление читают агенты, и оно не связано с enum ничем, кроме внимательности автора;
5. CHECK на adapt_findings.category в схеме БД.

ОСОБО: докстринг harness/claude/mcp/project/tools_adapt.py:5 УТВЕРЖДАЕТ «No mirror to keep in sync: harness/claude/mcp is the single canonical tree», держа при этом зеркало константы сервиса. Утверждение верно про ДЕРЕВО (MCP не копируется по IDE) и ложно про КОНСТАНТУ. Это ровно тот класс, что разбирала renar-debt: строка утверждает о себе больше, чем заслужила.

ПОЧЕМУ ЭТО ДЕФЕКТ, ХОТЯ ВСЕ ЧЕТЫРЕ КОПИИ СЕЙЧАС СОВПАДАЮТ. Совпадение — не свойство конструкции, а состояние. Ровно так же выглядел список типов SPEC до ADR-013: пять мест, все согласованные, до дня, когда стандарт сдвинулся, и тогда разошлись все пять поодиночке. §7.4.4 — норма ВНЕШНЯЯ, мы её не контролируем.

ПРЕЦЕДЕНТ И ГОТОВЫЙ ПРИЁМ, НЕ НАДО ИЗОБРЕТАТЬ. spec-closed-list в #200 свела пять мест в одно: модуль MCP стал ЧИТАТЬ константу вместо зеркала, число форматируется из len(), детектор второго литерального перечня (LIST_RE в tests/test_spec_types_closed_list.py) краснеет на второй копии. Здесь тот же ход, и LIST_RE надо ОБОБЩИТЬ на категории находок, а не копировать: копия детектора есть тот же дефект уровнем выше. В смене #201 LIST_RE был намеренно оставлен суженным до типов SPEC, и причина записана прямо в тесте.

ЧТО ПРОВЕРИТЬ ПРИ ПЛАНИРОВАНИИ И ЧЕГО НЕ РАЗРЕЗАТЬ. Перечисление прозой в description MCP снять НЕЛЬЗЯ молча — это то, по чему агент выбирает категорию; его надо СОБИРАТЬ из константы, а не удалять. Импорт service_adapts в renar_clause_reactive_adapt проверить на цикл: renar_clause_reactive_adapt уже импортируется из renar_conformance. Состав списка и статусы ADAPT не трогать — статусы разбирает adapt-status-enum-diverged-from-the-standards-closed-list.

## Acceptance Criteria

## Plan

## Rollback

## Journal
