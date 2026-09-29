---
slug: lazily-created-table-is-a-second-route-into-the-hybrid-state
title: "Путь в гибридное состояние через ЛЕНИВО созданную таблицу не закреплён тестом"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_upgrade_from_1_8.py"
scope_paths:
  - "tests/test_upgrade_from_1_8.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T14:32:53Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Сообщённый случай закреплён тестом. Отчёт с чужого проекта: миграция 1.7→1.9 упала на duplicate column name declared_scope_status, стамп 37, таблица verification_runs. Воспроизведено: без стража ошибка дословная, со стражем 1.10 цепочка от 37 доходит до 67. Существующий регрессионный тест закрывает КЛАСС, но через таблицу, которую создаёт init_schema при установке; здесь путь другой — verification_runs создаётся ЛЕНИВО на первом verify, и именно поэтому оказалась новой формы при старом стампе.

## Acceptance Criteria

1. Тест строит состояние из отчёта: стамп 37 и verification_runs новой формы, и требует, чтобы цепочка дошла до текущей версии. 2. НЕГАТИВНЫЙ: тест обязан краснеть без стража — проверяется прямым вызовом тех же операторов миграции без него, иначе тест не доказывает, что страж что-то держит. 3. Полная лента зелёная.

## Plan

## Rollback

git revert; добавляется тест, поведение не меняется.

## Journal

- 2026-09-29T14:32:14Z [implementation] — AC-1: ✓ tests/test_upgrade_from_1_8.py::test_a_lazily_created_table_is_the_other_route_into_the_hybrid_state — строит стамп 37 при verification_runs текущей формы и требует, чтобы цепочка дошла до SCHEMA_VERSION. AC-2 НЕГАТИВНЫЙ: ✓ ::test_without_the_guard_that_same_state_raises_the_reported_error — те же операторы в обход стража дают сообщённое duplicate column name; без этой пары первый тест проходил бы и на цепочке, которой нечего было пережить. AC-3: ✓ полная лента 12321 прошли, 34 пропущены. Domain: воспроизведено ДО написания теста, оба конца — ошибка дословная без стража, 37 → 67 со стражем.
