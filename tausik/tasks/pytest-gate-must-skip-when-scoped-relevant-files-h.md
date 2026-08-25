---
slug: pytest-gate-must-skip-when-scoped-relevant-files-h
title: "pytest gate must skip when scoped relevant_files have no test mapping"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: light
call_budget: 25
defect_of: stack-schema-design
scope: "scripts/gate_runner.py, tests/test_gates.py, CHANGELOG.md, CLAUDE.md (если требует уточнения)"
scope_exclude: null
relevant_files:
  - "scripts/gate_runner.py"
  - "scripts/gate_test_resolver.py"
  - "tests/test_gates.py"
  - CHANGELOG.md
  - CLAUDE.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T15:36:47Z"
---

## Goal

Fix gate_runner.run_command_gate / run_gates: when {test_files_for_files} placeholder is in cmd AND relevant_files is non-empty AND resolve_test_files_for_relevant returns empty → emit skipped_result, NOT fallback to 'tests/' (full suite). Fallback to full suite stays only when relevant_files is empty (no scoping data). Aligns with CLAUDE.md spec ('гонит только tests/test_<basename>.py').

## Acceptance Criteria

1. scripts/gate_runner.py: при relevant_files=non-empty + resolve_test_files_for_relevant=[] добавлен ранний skipped_result в run_gates (или эквивалент в run_command_gate) — НЕ fallback на 'tests/'.
2. Когда relevant_files=[] (без scoping) — поведение не меняется, fallback на полный suite сохраняется.
3. Сообщение skipped_result явно объясняет: 'No test file maps to relevant_files via tests/test_<basename>.py heuristic; gate skipped (scoped run).'
4. Добавлен/обновлён тест в tests/test_gates.py: case_no_test_mapping_skipped (relevant_files=[some_module.py] без test_some_module.py → result.skipped=True), case_empty_relevant_falls_back (relevant_files=[] → не skip, доходит до cmd).
5. Существующие тесты в tests/test_gates.py не сломаны (pytest tests/test_gates.py -v).
6. CHANGELOG.md обновлён под v1.4.2 (defect-fix).
7. CLAUDE.md QG-2 описание не противоречит фиксу — если нужно уточнить, обновить.

## Plan

## Rollback

## Journal

- 2026-04-25T15:35:44Z [implementation] — AC verified: 1. ✓ scripts/gate_runner.py — добавлен _SCOPED_SKIP_SENTINEL; run_command_gate возвращает (True, sentinel) при relevant_files=non-empty + resolve_test_files=[]; run_gates переводит sentinel в skipped_result. 2. ✓ relevant_files=[] → fallback на 'tests/' сохраняется (test_unscoped_call_falls_back_to_full_suite passes). 3. ✓ Сообщение skip: 'No test file maps to relevant_files via tests/test_<basename>.py heuristic; gate skipped (scoped run).' — точно по AC. 4. ✓ tests/test_gates.py — добавлены test_scoped_run_with_no_test_mapping_skips, test_unscoped_call_falls_back_to_full_suite, test_run_gates_translates_scoped_skip_into_skipped_result; старый test_substitution_falls_back_to_full_suite заменён (его prev-поведение и было дефектом). 5. ✓ pytest tests/test_gates.py -q → 84 passed in 2.17s, no regressions. 6. ✓ CHANGELOG.md обновлён под Unreleased — секция "Fixed — pytest gate scoped-skip" + "Test Coverage". 7. ✓ CLAUDE.md строка 28 (QG-2 описание) уточнена: "Если relevant_files non-empty но ни один тест не маппится → gate SKIPPED. Без relevant_files — fallback сохраняется".
- 2026-04-25T15:36:43Z [implementation] — Filesize fix: gate_runner.py был 433 → выделил resolve_test_files_for_relevant в scripts/gate_test_resolver.py (77 строк), shim re-export в gate_runner.py. Итог: gate_runner.py 370 строк (под 400 лимитом), все 84 теста test_gates.py проходят. Импорт resolve_test_files_for_relevant из gate_runner сохраняется (back-compat для других consumers).
- 2026-04-25T15:36:57Z [done] — Root cause: при имплементации scoped pytest gate (commit 885e445) был выбран "regression-safe" fallback на полный suite когда resolve_test_files_for_relevant возвращает []. Это покрывало два разных кейса одним поведением: (a) caller не передал relevant_files (legacy unscoped path) — fallback корректен; (b) caller передал relevant_files но ни один не маппится на test_<basename>.py (новый модуль без тестов) — fallback НЕ корректен, противоречит scoping promise. Нужно было различать (a) и (b) с самого начала. Урок: regression-safe defaults для scoped APIs должны проверять "scope provided" vs "scope provided but resolution empty" — это разные состояния.
