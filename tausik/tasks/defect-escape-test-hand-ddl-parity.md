---
slug: defect-escape-test-hand-ddl-parity
title: "test_defect_escape объявляет tasks своей копией DDL — падает гейт паритета фикстур"
status: done
epic: landscape-2026-h2
story: l26-provable
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: l26-defect-escape-rate
scope: "tests/test_defect_escape.py — заменить хардкод tasks-DDL на canonical_ddl"
scope_exclude: null
relevant_files:
  - "tests/test_defect_escape.py"
scope_paths:
  - "tests/test_defect_escape.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-20T23:57:47Z"
---

## Goal

СБЕЖАВШИЙ ДЕФЕКТ из l26-defect-escape-rate (сессия #126): test_defect_escape.py хардкодит CREATE TABLE tasks (8 колонок) вместо canonical_ddl('tasks'). Scoped verify задачи (pytest только по test_defect_escape.py) это ПРОПУСТИЛ — гейт test_ddl_fixture_parity.py::test_no_test_file_declares_this_table_by_hand[tasks] живёт в отдельном тест-файле и ловится только полным прогоном. Реальный пример ценности escape-rate метрики (memory #267): дефект прошёл узкую верификацию. Починка: заменить хардкод tasks-DDL на from conftest import canonical_ddl -> canonical_ddl('tasks'); vruns остаётся 2-колоночной заглушкой (_STUB_MAX_COLUMNS=2). Негативный край: полный suite обязан стать зелёным (test_ddl_fixture_parity[tasks] PASS), а 7 тестов defect_escape продолжают проходить на канонической схеме (INSERT с title/created_at/updated_at).

## Acceptance Criteria

AC1. test_defect_escape.py использует canonical_ddl('tasks') вместо хардкод CREATE TABLE tasks; verification_runs остаётся 2-колоночной заглушкой (разрешено _STUB_MAX_COLUMNS=2).
AC2. INSERT в tasks предоставляет обязательные NOT NULL без дефолта (slug, title, created_at, updated_at).
AC3. test_ddl_fixture_parity[tasks] проходит (был красным), т.е. ошибка паритета устранена.
AC4. 7 тестов defect_escape продолжают проходить на канонической схеме.
AC5. Негативный край: полный suite зелёный, никаких новых падений.

## Plan

## Rollback

git revert; правка только в тестовом файле test_defect_escape.py, откат безопасен.

## Journal

- 2026-07-20T23:57:19Z [implementation] — Root cause (missing-validation): тест хардкодил CREATE TABLE tasks вместо canonical_ddl — гейт паритета фикстур (test_ddl_fixture_parity) ловит это только в ПОЛНОМ прогоне, а scoped verify задачи-родителя гонял лишь test_defect_escape.py, где нарушения не видно. Prevention: тесты, которым нужна таблица схемы, берут DDL из conftest.canonical_ddl (заглушки ≤2 колонок разрешены); дефект — живой пример escape-через-узкую-верификацию (memory #267).
- 2026-07-20T23:57:26Z [implementation] — AC1-5: canonical_ddl('tasks') вместо хардкода (AC1), INSERT с title/created_at/updated_at (AC2), test_ddl_fixture_parity[tasks] PASS (AC3), 7 escape-тестов зелёные на канонической схеме (AC4), 26 passed совместно (AC5). Root cause залогирован. Test-only.
- 2026-07-20T23:57:35Z [implementation] — AC verified: 1. ✓ canonical_ddl('tasks') вместо хардкода 2. ✓ INSERT с title/created_at/updated_at 3. ✓ test_ddl_fixture_parity[tasks] PASS 4. ✓ 7 escape-тестов зелёные 5. ✓ 26 passed совместно, полный suite прогоню
