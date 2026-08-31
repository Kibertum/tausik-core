---
slug: adapt-finding-categories-count-is-written-not-derived
title: "Число категорий находок ADAPT написано рядом со списком, а не выведено из него"
status: planning
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: simple
role: developer
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

НАЙДЕНО ДЕТЕКТОРОМ ЗАДАЧИ spec-closed-list-is-nine-while-the-standard-has-eleven В #200, НЕ ПРЕДПОЛОЖЕНИЕ. Тест test_no_hand_written_count_beside_the_list, написанный для типов SPEC, при первом же прогоне указал на ТОТ ЖЕ класс в списке категорий обратных находок ADAPT: scripts/service_adapts.py несёт литералы «CLOSED list of 7» и «closed list of 7», harness/claude/mcp/project/tools_adapt.py — «CLOSED list of 7». Число написано РЯДОМ со списком, а не выведено из него.
ПОЧЕМУ ЭТО ДЕФЕКТ, ХОТЯ ЧИСЛО СЕЙЧАС ВЕРНОЕ. §7.4.4 закрывает категории на семи, и сегодня у нас ровно семь — то есть наблюдаемого расхождения НЕТ. Ровно так же выглядел список типов SPEC до ADR-013: число было верным, пока стандарт не сдвинулся, и в тот же день справка начала врать. Верный литерал есть тот же дефект, отложенный до следующей поправки стандарта, и чинить его дешевле сейчас.
СМЕЖНОЕ, ПРОВЕРИТЬ В ЭТОЙ ЖЕ ЗАДАЧЕ: у ADAPT есть ВТОРОЙ закрытый список — статусы. Он разошёлся со стандартом в обе стороны и разбирается отдельной задачей adapt-status-enum-diverged-from-the-standards-closed-list; здесь только АРИФМЕТИКА (число выводится из списка), состав не трогать, чтобы задачи не слиплись.
ГОТОВЫЙ ИНСТРУМЕНТ: детектор уже написан и работает — tests/test_spec_types_closed_list.py, COUNT_RE плюс LIST_RE. В #200 он был СУЖЕН до типов SPEC именно для того, чтобы не расширять чужую задачу молча. Здесь его надо ОБОБЩИТЬ на любой закрытый список (типы SPEC, категории находок, статусы), а не копировать: копия детектора — тот же дефект второго литерала, только уровнем выше.
НЕГАТИВНЫЙ СЦЕНАРИЙ ДЛЯ AC: обобщённый детектор ОБЯЗАН краснеть на литеральном числе рядом со списком ДАЖЕ КОГДА ЧИСЛО СОВПАДАЕТ с длиной списка; тест, зелёный при совпадении, не отличает выведенное число от написанного и предмета задачи не проверяет.

## Acceptance Criteria

## Plan

## Rollback

## Journal
