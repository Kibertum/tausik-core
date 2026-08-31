---
slug: adr-013-conditional-obligations-expire-when-subject-appears
title: "Условные обязанности ADR-013 для SPEC-TEST и SPEC-DOC объявлены неприменимыми — объявление истекает машиной"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: medium
role: architect
stack: null
tier: null
call_budget: null
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

ЗАВЕДЕНА В #200 ПРИ ЗАКРЫТИИ spec-closed-list-is-nine-while-the-standard-has-eleven, КАК ЯВНОЕ ОБЪЯВЛЕНИЕ ВМЕСТО МОЛЧАЛИВОГО ПРОПУСКА. Расширение закрытого списка до одиннадцати ввело типы SPEC-TEST и SPEC-DOC, у каждого из которых ADR-013 несёт УСЛОВНУЮ обязанность. Сегодня обе НЕПРИМЕНИМЫ, и это проверено, а не предположено.
(1) TC.environment-ref на SPEC-TEST, обязателен при automation.kind: dynamic (§9, стр.119 и стр.672). НЕПРИМЕНИМО: TC не существует у нас как класс артефакта — в sqlite_master нет ни одной таблицы TC (проверено запросом). Обязанности не к чему предъявить. Вакуумная истина здесь ЗАКОННА, ровно по тому же основанию, по которому она законна для tc-pos-neg-pairing и НЕЗАКОННА для происхождения SPEC: там предмет есть и обязанность нарушена, здесь предмета нет вовсе.
(2) Док-линт для SPEC-DOC, без которого неверифицируемый SPEC не проходит QG-2. НЕПРИМЕНИМО СЕГОДНЯ: артефактов типа SPEC-DOC у нас ноль. scripts/docs_lint.py существует, но он warning-only (exit 0 всегда) и к SPEC-DOC не привязан — то есть при появлении первого SPEC-DOC обязанность станет живой, а исполнителя у неё не будет.
СРОК ЖИЗНИ ОБЪЯВЛЕНИЯ ОГРАНИЧЕН МАШИНОЙ, А НЕ ПАМЯТЬЮ: тест test_adr_013_conditional_obligations_are_still_vacuous в tests/test_spec_types_closed_list.py КРАСНЕЕТ, как только предпосылка перестаёт держаться — появляется строка SPEC-DOC или появляется таблица TC. Тогда эта задача становится срочной сама, без чьего-либо напоминания.
ЧТО ДЕЛАТЬ, КОГДА ПОКРАСНЕЕТ: привязать docs_lint к SPEC-DOC и сделать его блокирующим для этого типа (граница SPEC-DOC и SPEC-OPS проходит по составу поставки, а не по жанру текста); для SPEC-TEST — ввести environment-ref в момент, когда TC появятся как класс, и помнить §9 стр.672: поле заполняет НЕ генератор, а архитектор или runner ПОСЛЕ генерации, иначе ломается изоляция §9.19.2.

## Acceptance Criteria

## Plan

## Rollback

## Journal
