---
slug: spec-closed-list-is-nine-while-the-standard-has-eleven
title: "Закрытый список типов SPEC у нас девять, в стандарте одиннадцать — и справка врёт числом"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: null
role: developer
stack: python
tier: moderate
call_budget: 60
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

`tausik spec add --help` печатает буквально «Closed list of 9 RENAR types» и принимает ARCH, API, DATA, INT, PROC, UI, AI, SEC, OPS. RENAR ADR-013 (accepted) добавил SPEC-TEST (тестовые стенды и данные) и SPEC-DOC (поставляемая документация), доведя закрытый список до одиннадцати. Довод стандарта механический и нам близкий: инвалидация verified срабатывает при ЛЮБОМ инкременте версии артефакта, поэтому при привязке TC к стенду через SPEC-OPS правка процедуры деплоя обрушивала бы в approved ВСЕ TC, ссылающиеся на этот SPEC-OPS. Отдельный тип делает инвалидацию точной. Обвязка, которую нельзя потерять: TC.environment-ref на SPEC-TEST УСЛОВНО обязателен — только при automation.kind dynamic, статические проверки стенда не требуют; для SPEC-DOC обязателен док-линт, иначе неверифицируемый SPEC не проходит QG-2; граница SPEC-DOC и SPEC-OPS проходит по составу поставки, а не по жанру текста. Задача включает миграцию схемы и проверку, что число в справке выводится из списка, а не написано отдельно — иначе следующий сдвиг снова разойдётся с текстом.

## Acceptance Criteria

## Plan

## Rollback

## Journal
