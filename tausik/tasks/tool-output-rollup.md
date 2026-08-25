---
slug: tool-output-rollup
title: "Token-эргономика: rollup вербозного вывода инструментов вместо дампа (заимствование cubest)"
status: done
epic: landscape-2026-h2
story: borrow-cubest-onyx
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "Новый scripts/rollup_render.py (общий агрегатор+бюджет-ручки) + точечное подключение в 2-3 scripts/project_cli_*.py + tests/test_rollup_render.py"
scope_exclude: "Изменение данных/схемы БД; l26-tool-token-cost (стоимость тул-ДЕФИНИЦИЙ — отдельная задача); декларативные YAML-профили cubest (отложены, при необходимости отдельной задачей)"
relevant_files:
  - "scripts/output_rollup.py"
  - "scripts/project_cli_events.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser.py"
  - "scripts/project_parser_task.py"
  - "tests/test_output_rollup.py"
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-27T12:55:58Z"
---

## Goal

Снизить токен-стоимость вербозных выводов TAUSIK для агента, сворачивая их в компактный иерархический rollup (по образцу cubest: dimensions×measures + бюджет-ручки top_n/min_count/max_lines), вместо построчного дампа. Цель — те выводы, что агент читает часто и которые растут с размером проекта: events (аудит-лог), task list больших эпиков, metrics, git-status в проверках. Общий рендерер + подключение к 2-3 самым дорогим командам, с флагом --full для полного вывода. Не менять данные/схему — только представление.

## Acceptance Criteria

1. Rollup-рендерер: N строк вывода сворачиваются в компактный иерархический агрегат (группировка по измерениям + счётчики/агрегаты) с ДЕТЕРМИНИРОВАННЫМ порядком. 2. Бюджет-ручки top_n/max_lines/min_count работают и печатают ЗНАМЕНАТЕЛЬ (сколько строк скрыто), а не молча обрезают. 3. Подключено к ≥2 дорогим командам (например events и task list большого эпика); флаг --full возвращает полный прежний вывод. 4. НЕГАТИВ: ввод меньше порога НЕ сворачивается (rollup не прячет данные, когда экономии нет), а --full ВСЕГДА обходит rollup. 5. Не меняет данные/схему/семантику — только представление: тест доказывает, что --full байт-в-байт равен прежнему выводу на выборке. 6. Полный scoped verify зелёный.

## Plan

## Rollback

Чистое представление поверх существующих данных. Откат: флаг --full даёт прежний вывод немедленно; git revert коммита убирает rollup целиком. Не трогает схему/данные/семантику.

## Journal

- 2026-07-27T12:54:40Z [implementation] — AC verified: 1. ✓ tests/test_output_rollup.py::TestRenderRollup::{test_deterministic_order_and_counts,test_same_input_same_output} — N rows → count-per-group aggregate, ordered count-desc then key-asc (deterministic). Live: 57 tasks→4 groups, 200 events→6 groups. 2. ✓ TestRenderRollup::{test_top_n_prints_denominator,test_max_lines_is_stricter_of_the_two,test_min_count_hides_and_counts} — all three knobs work; footer prints denominator ('N more group(s), M row(s) not shown', min_count named). No silent truncation. 3. ✓ Wired into 2 commands: cmd_events (entity_type/action) + cmd_task list (status/role). --full flag added to both parsers via output_rollup.add_rollup_flags. TestEventsWiring + TestTaskListWiring exercise both. 4. ✓ NEGATIVE: TestShouldRollup::{test_full_never_rolls_up,test_below_threshold_is_full} + TestEventsWiring/TestTaskListWiring::test_below_threshold_is_byte_identical — below 25 rows NOT collapsed; --full ALWAYS bypasses at any size. 5. ✓ AC5 byte-identical: TestEventsWiring::test_full_flag_is_byte_identical_above_threshold + TestTaskListWiring::test_full_flag_is_byte_identical_above_threshold compare --full output to an oracle (per-event loop / _print_table) — exact string equality. No data/schema/semantics change (presentation only). 6. ✓ tausik verify --task standard: pytest PASS scoped over 5 mapped files. ruff + mypy clean on output_rollup.py + all edited scripts. 215 event/task/parser tests pass (no regression). Domain: live task list/events on the 1173-task DB produce valid, useful aggregates.
- 2026-07-27T12:55:56Z [implementation] — AC verified: 1. ✓ tests/test_output_rollup.py::TestRenderRollup::{test_deterministic_order_and_counts,test_same_input_same_output}. Live: 57 tasks→4 groups, 200 events→6 groups. 2. ✓ TestRenderRollup::{test_top_n_prints_denominator,test_max_lines_is_stricter_of_the_two,test_min_count_hides_and_counts} — knobs work + denominator footer, no silent truncation. 3. ✓ Wired to cmd_events (entity_type/action) + cmd_task list (status/role); --full/--top-n/--max-lines added via add_rollup_flags. TestEventsWiring + TestTaskListWiring. 4. ✓ NEGATIVE: TestShouldRollup + test_below_threshold_is_byte_identical — <25 rows not collapsed; --full always bypasses. 5. ✓ AC5 byte-identical: test_full_flag_is_byte_identical_above_threshold (events + task list) vs oracle. Presentation only. 6. ✓ verify --task standard pytest PASS; ruff+mypy clean; filesize gate green (project_parser.py=400, import moved to module top); 215 related tests pass. Domain: live 1173-task DB aggregates valid.
