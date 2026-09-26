---
slug: the-tree-drops-fields-and-the-gate-cannot-see-it
title: "Экспорт дерева молча теряет поля, а гейт оборота это увидеть не может"
status: planning
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
---

## Goal

НАЙДЕНО ПРИ ПОЧИНКЕ is-code-needed-at-all-before-writing-it, смена #277. Там уже исправлены resolution и resolution_reason, но причина общая и остаётся.

ПОЧЕМУ ГЕЙТ СЛЕП ПО ПОСТРОЕНИЮ: tests/test_state_roundtrip_gate.py пере-сериализует БД и побайтово сравнивает результат с деревом. ОБЕ стороны сравнения порождает один и тот же экспортёр, поэтому колонка, которую он не выбирает в SELECT, не может появиться ни на одной из сторон. Гейт зелен при любом числе забытых полей и будет зелен всегда.

ЗАМЕР: в таблице tasks 34 колонки. Кроме уже исправленных двух, деревом НЕ переносится как минимум tracker_refs — поле, добавленное в 1.9 и показываемое `task show`, то есть ссылка на тикет теряется на клоне. Дальше требуют разбора: started_at (при том, что completed_at переносится), started_model_id, done_model_id, model_mismatch (это доказательства разделения обязанностей SENAR), no_file_changes_declared, token_budget, cost_budget_usd (при том, что call_budget переносится). Асимметрия «бюджет переносим, два других бюджета нет» сама по себе подозрительна.

ЧТО СДЕЛАТЬ, И ЭТО НЕ «ДОБАВИТЬ ПОЛЯ»: каждая колонка tasks обязана быть либо экспортируемой, либо ОБЪЯВЛЕННОЙ как непереносимая с причиной, а тест обязан требовать, чтобы объединение двух списков покрывало таблицу целиком. Тогда следующая новая колонка заставит принять решение, а не будет забыта молча. Это ровно та же форма, что конвенция #755 про корпус сквозного теста: проверка, сравнивающая порождённое с порождённым, не видит пропуска.

РАЗДЕЛИТЬ ЧЕСТНО: часть колонок непереносима правильно (id, story_id, created_at, archived_at, claimed_by, score, risk_score, attempts, call_actual, tokens_actual, cost_actual_usd — это телеметрия и внутренние ключи, а не замысел). Задача не в том, чтобы вынести всё, а в том, чтобы решение было записано.

## Acceptance Criteria

## Plan

## Rollback

## Journal
