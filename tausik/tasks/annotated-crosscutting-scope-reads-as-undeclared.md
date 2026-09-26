---
slug: annotated-crosscutting-scope-reads-as-undeclared
title: "Аннотированное объявление области читается парсером как отсутствие объявления"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: simple
role: backend
stack: null
tier: trivial
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_test_resolver.py"
  - "tests/test_crosscutting_annotated.py"
scope_paths:
  - "scripts/gate_test_resolver.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T20:20:20Z"
resolution: null
resolution_reason: null
---

## Goal

ВОСПРОИЗВЕДЕНИЕ, сессия #181: scripts/gate_test_resolver.py::read_crosscutting_scope обходит тело модуля и сопоставляет ТОЛЬКО ast.Assign. Форма 'CROSSCUTTING_SCOPE: list[str] = []' — это ast.AnnAssign, и функция возвращает None, то есть 'файл не объявляет ничего'. Автор при этом объявление НАПИСАЛ. Отказ в tests/test_crosscutting_registry.py выглядит как забытое объявление, а не как непонятая форма, поэтому первый вывод читателя — 'я забыл', и он ищет не там; я потратил на это цикл лично. Класс шире одного файла: тот же парсер читает объявления для скоуп-гейта pytest, где промах не краснеет вовсе, а молча расширяет прогон. Соседняя функция _own_public_members в scripts/gate_class_surface.py разбирает ОБЕ формы, Assign и AnnAssign — то есть в этой же кодовой базе правило уже записано верно, и расхождение между двумя разборщиками одного вида объявления и есть дефект.

## Acceptance Criteria

1. Воспроизведено тестом до правки: файл с 'CROSSCUTTING_SCOPE: list[str] = ["docs/"]' читается read_crosscutting_scope как None.
2. После правки обе формы — Assign и AnnAssign — читаются одинаково; тест на обе.
3. НЕГАТИВНЫЙ: аннотация без значения ('CROSSCUTTING_SCOPE: list[str]') и не-литеральное значение по-прежнему дают None, а не пустой список.
4. CHANGELOG EN+RU.

## Plan

## Rollback

git revert коммита; правка локальна в read_crosscutting_scope

## Journal

- 2026-09-23T20:19:18Z [implementation] — AC-1: ✓ tests/test_crosscutting_annotated.py::test_both_forms_read_the_same
- 2026-09-23T20:19:18Z [implementation] — Воспроизведено тестом до правки: 2 красных (annotated, annotated opt-out). Правка в read_crosscutting_scope: Assign и AnnAssign со значением. Файл собран из HEAD с двумя точечными правками (своей и прошлой — фикстуры .sql), 500 строк: Edit-хук переформатировал бы весь файл (память записана).
- 2026-09-23T20:19:19Z [implementation] — AC-2: ✓ tests/test_crosscutting_annotated.py::test_the_annotated_opt_out_is_an_empty_list
- 2026-09-23T20:19:19Z [implementation] — AC-3: ✓ tests/test_crosscutting_annotated.py::test_no_value_or_a_computed_value_is_still_undeclared
- 2026-09-23T20:19:20Z [implementation] — AC-4: ✓ CHANGELOG EN+RU
