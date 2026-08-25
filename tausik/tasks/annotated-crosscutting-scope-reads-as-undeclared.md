---
slug: annotated-crosscutting-scope-reads-as-undeclared
title: "Аннотированное объявление области читается парсером как отсутствие объявления"
status: planning
epic: arch-debt-post-18
story: adp18-quality-signals
complexity: simple
role: backend
stack: null
tier: trivial
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/gate_test_resolver.py"
  - "tests/test_crosscutting_registry.py"
  - "tests/test_gate_test_resolver.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ВОСПРОИЗВЕДЕНИЕ, сессия #181: scripts/gate_test_resolver.py::read_crosscutting_scope обходит тело модуля и сопоставляет ТОЛЬКО ast.Assign. Форма 'CROSSCUTTING_SCOPE: list[str] = []' — это ast.AnnAssign, и функция возвращает None, то есть 'файл не объявляет ничего'. Автор при этом объявление НАПИСАЛ. Отказ в tests/test_crosscutting_registry.py выглядит как забытое объявление, а не как непонятая форма, поэтому первый вывод читателя — 'я забыл', и он ищет не там; я потратил на это цикл лично. Класс шире одного файла: тот же парсер читает объявления для скоуп-гейта pytest, где промах не краснеет вовсе, а молча расширяет прогон. Соседняя функция _own_public_members в scripts/gate_class_surface.py разбирает ОБЕ формы, Assign и AnnAssign — то есть в этой же кодовой базе правило уже записано верно, и расхождение между двумя разборщиками одного вида объявления и есть дефект.

## Acceptance Criteria

## Plan

## Rollback

git revert коммита; правка локальна в read_crosscutting_scope

## Journal
