---
slug: direct-modification-has-one-recognized-case
title: "Прямая правка артефакта: документация называет ОДИН признанный случай и датирует список (SENAR 1.5 §4.1, 8.6(j))"
status: done
epic: release-110-deferred-from-19
story: release110-senar-15-claimed-honestly
complexity: simple
role: docs
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_bypass_record.py"
  - "scripts/project_cli_events.py"
  - "tests/test_direct_edit_recognized_case.py"
  - "tests/test_direct_edit_bypass_record.py"
scope_paths:
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - "scripts/gate_bypass_record.py"
  - "scripts/project_cli_events.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T19:03:51Z"
---

## Goal

SENAR 1.4 перечислял пять законных случаев ручной правки, 1.5 признаёт один (среда, где агента запустить нельзя) и требует датировать список и привязать его к пересмотру по 10.13; запись обхода обязательна во всех случаях. docs/ru|en/cli.md «Обход гейта записывается (§8.6(j))» и докстринг gate_bypass_record.py несут редакцию 1.4. Цель: текст приведён к 1.5, цитирует дату редакции, тест держит фразу отказа по живому вызову (конвенция #698).

## Acceptance Criteria

1. cli.md (RU/EN) и докстринг gate_bypass_record описывают один признанный случай, датируют список и ссылаются на 10.13.
2. Текст записи обхода в CLI печатает ту же формулировку; тест снимает её живым вызовом.
3. НЕГАТИВНЫЙ: обход без записи по-прежнему невозможен — существующие тесты gate_bypass_record зелены.
4. CHANGELOG EN+RU.

## Plan

## Rollback

git revert.

## Journal

- 2026-09-23T18:41:35Z [implementation] — Сделано: gate_bypass_record — RECOGNIZED_CASE и RECOGNIZED_AS_OF (SENAR 1.5 §4.1, редакция 2026-09-07, пересмотр по §10.13), докстринг переписан под 1.5, отказ без --rationale называет один случай с датой; cli.md en/ru: раздел §8.6(j) под 1.5, пример --rationale сменён, четыре случая 1.4 названы как решаемые агентскими средствами. Тест держал формулировку 1.4 ('incident', 'does not run') — переписан на признанный случай. Новый tests/test_direct_edit_recognized_case.py снимает отказ живым вызовом cmd_events_emit_supervision и сверяет с docs. 24 теста зелёные.
- 2026-09-23T19:03:46Z [implementation] — AC verified: 1. ✓ cli.md en/ru и докстринг gate_bypass_record — один признанный случай, дата редакции 2026-09-07, ссылка на §10.13 2. ✓ test_the_live_refusal_names_one_dated_case, test_the_english_docs_quote_the_live_refusal (живой вызов cmd_events_emit_supervision) 3. ✓ НЕГАТИВНЫЙ: 19 тестов test_direct_edit_bypass_record зелёные, запись без rationale отказывается (exit 2) 4. ✓ CHANGELOG EN+RU. Verify #2743 зелёный.
