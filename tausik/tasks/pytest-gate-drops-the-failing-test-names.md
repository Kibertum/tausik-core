---
slug: pytest-gate-drops-the-failing-test-names
title: "The pytest gate prints '=== FAILURES ===' and drops the names of the failing tests — a red verify does not say what is red"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_runner.py"
  - "tests/test_gate_output_keeps_failures.py"
  - "tests/test_gate_command_runner.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/gate_runner.py"
  - "scripts/render_verify.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
  - "docs/ru/*.md"
  - "docs/en/*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T17:17:25Z"
resolution: null
resolution_reason: null
---

## Goal

Measured three times in session #263: a scoped verify came back '[FAIL] pytest (block)' followed by the '=== FAILURES ===' banner and nothing else — the gate runner truncates the pytest output to a handful of lines and the short summary with the FAILED names is cut off. The agent found the red tests only by reproducing the selection through gate_command_runner.resolve_test_files_for_relevant and running pytest by hand; a user without that trick reruns the full lane, which is the pattern decision #371 forbids. Fix: the pytest gate always carries the 'short test summary info' block (the FAILED/ERROR lines) into the gate output and the verify report, whatever the truncation limit does to the rest; the same for the slow-only case — a scoped run that selects no test because every file is slow-marked says so and names TAUSIK_VERIFY_FULL=1 instead of CANNOT-RUN.

## Acceptance Criteria

1. Упавший гейт в отчёте verify (CLI и MCP — общий format_results) всегда несёт строки FAILED/ERROR из short test summary и строку итога pytest (N failed, M passed), где бы они ни стояли в выводе; обрезка режет остальное.
2. Воспроизведено тестом ДО правки: вывод из многих пакетов, где FAILED стоит после 5-й строки, — имя упавшего теста в отчёт не попадает.
3. НЕГАТИВНЫЙ: вывод без итоговых строк pytest (не pytest-гейт, крах) печатает начало и конец вывода, а не пустоту; прошедший гейт не печатает тело.
4. Случай «все выбранные тесты slow» остаётся с сообщением про TAUSIK_VERIFY_FULL=1 (существующий тест не тронут).
5. CHANGELOG EN+RU.

## Plan

## Rollback

git revert; output shaping only

## Journal

- 2026-09-23T17:17:19Z [implementation] — AC verified: 1 — format_results → failure_excerpt: начало, все FAILED/ERROR и итоги pytest, конец (tests/test_gate_output_keeps_failures.py::test_the_failing_test_name_reaches_the_report на выводе реального пакетного прогона смены #266). 2 — ::test_the_old_head_alone_would_have_lost_it фиксирует дефект. 3 — НЕГАТИВ ::test_output_without_pytest_lines_keeps_head_and_tail, ::test_a_passing_gate_prints_no_body. 4 — случай slow-only не тронут (сообщение TAUSIK_VERIFY_FULL=1 в gate_command_runner). 5 — CHANGELOG EN+RU; test_gate_command_runner::test_a_failing_scoped_gate_keeps_five_lines_of_failure пересмотрен: он закреплял сам дефект. Verify #2699 зелёный.
- 2026-09-23T17:17:20Z [implementation] — verify #2699 green; tests/test_gate_output_keeps_failures.py 5 tests incl. 2 negatives
