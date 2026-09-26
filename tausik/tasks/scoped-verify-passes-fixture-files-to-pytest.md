---
slug: scoped-verify-passes-fixture-files-to-pytest
title: "Verify-гейт передаёт pytest не-Python файл из tests/ (фикстуру .sql) — pytest ничего не собирает, и гейт отвечает CANNOT-RUN"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: simple
role: developer
stack: python
tier: light
call_budget: null
defect_of: upgrade-from-1-8-crashes-at-v53-and-leaves-the-version-at-44
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_test_resolver.py"
  - "tests/test_gate_resolver_skips_fixture_files.py"
scope_paths:
  - "scripts/gate_test_resolver.py"
  - "tests/test_gate_resolver_skips_fixture_files.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T18:50:45Z"
resolution: null
resolution_reason: null
---

## Goal

Объявленный в relevant_files файл под tests/, не являющийся модулем Python (фикстура .sql, .json), не попадает в список путей pytest; остальные тесты пакета собираются и бегут.

## Acceptance Criteria

1. resolve_test_files_for_relevant не возвращает путь под tests/, не оканчивающийся на .py. 2. Тестовый .py рядом с такой фикстурой по-прежнему возвращается. 3. НЕГАТИВНЫЙ: до правки pytest с путём фикстуры отвечал 'no tests ran' — тест держит поведение резолвера, а не вывод pytest. 4. CHANGELOG EN+RU.

## Plan

## Rollback

git revert одного условия в gate_test_resolver

## Journal

- 2026-09-23T18:32:06Z [implementation] — Причина: resolve_test_files_for_relevant принимал любой путь под tests/ как тест; фикстура .sql в argv pytest давала 'no tests ran' на весь пакет (воспроизведено: test_upgrade_from_1_8.py + .sql -> no tests ran; без .sql -> 5 passed). Правка: условие требует .py. Мутация: на старом условии оба новых теста красные, на новом зелёные. 158 тестов резолвера зелёные.
- 2026-09-23T18:32:07Z [implementation] — AC verified: 1. ✓ test_a_non_python_file_under_tests_is_not_returned 2. ✓ test_the_test_beside_the_fixture_is_still_returned 3. ✓ тест держит поведение резолвера; мутация старого условия даёт 2 failed 4. ✓ CHANGELOG EN+RU
