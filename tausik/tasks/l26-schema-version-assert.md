---
slug: l26-schema-version-assert
title: "Ассерт SCHEMA_VERSION == max(MIGRATIONS) на импорте"
status: done
epic: landscape-2026-h2
story: l26-hygiene
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "tests/test_migrations.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-18T10:51:48Z"
---

## Goal

SCHEMA_VERSION (backend_schema.py:6) и max(MIGRATIONS) (backend_migrations.py:331) синхронизируются РУКАМИ, ассерта нет. Забыть поднять одно из двух означает либо пропущенную миграцию, либо вечное состояние мигрировали-но-всё-ещё-устарело. Добавить проверку на импорте по образцу risk_model.py:54 (там ассерт суммы весов на 1.0). Негативный сценарий: рассинхрон вызывает явную ошибку, а не тихое расхождение.

## Acceptance Criteria

1. Рассинхрон SCHEMA_VERSION (backend_schema.py:6) и max(MIGRATIONS) (backend_migrations.py:331) обнаруживается автоматически, а не остаётся тихим. 2. Проверка срабатывает как можно раньше — на импорте либо отдельным тестом, по образцу ассерта суммы весов в risk_model.py:54. 3. НЕГАТИВНЫЙ СЦЕНАРИЙ: при искусственном рассинхроне проверка даёт явную ОШИБКУ с указанием обоих значений, а не тихо пропускает. 4. Существующие тесты миграций остаются зелёными; ruff чист.

## Plan

## Rollback

git revert; ассерт убирается

## Journal

- 2026-07-18T10:51:47Z [implementation] — AC-1: ✓ рассинхрон обнаруживается автоматически — check_schema_migration_parity(SCHEMA_VERSION, MIGRATIONS) вызывается на импорте backend_migrations. AC-2: ✓ проверка максимально ранняя (import-time), но вынесена в ФУНКЦИЮ, а не инлайн — иначе её нельзя протестировать; сознательно НЕ assert, потому что assert исчезает под python -O, то есть ровно тогда, когда гард нужнее всего. Импорт безопасен: backend_schema.py вообще без импортов, цикла нет. AC-3: ✓ НЕГАТИВ test_drift_raises_with_both_values_named — рассинхрон даёт RuntimeError, и в сообщении присутствуют ОБА значения (проверяется наличие 99 и v2), чтобы диагностика была самодостаточной. AC-4: ✓ вся сьюта миграций 21 passed на 3.11 И 3.13, ruff чист; +3 теста -> test_count 4750->4753, реген констант и бейджей, строгий doc-check зелёный. Domain: ошибка, которая раньше проявлялась как вечно-устаревшая БД у пользователя, теперь падает на ближайшей команде разработчика. Checklist: scope соблюдён, покрыт позитив/негатив/живые константы, security surface нет, rollback = git revert.
