---
slug: stale-noqa-comments-removed-with-a-ratchet
title: "ruff RUF100: 546 noqa comments suppress nothing"
status: planning
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
---

## Goal

The 546 noqa comments that suppress no active rule are removed in one hygiene change of their own, and RUF100 joins select so a stale suppression cannot accumulate again.

## Acceptance Criteria

## Plan

## Rollback

git revert

## Journal

- 2026-09-27T10:38:52Z [planning] — ЛОВУШКА ЗАМЕРА, найденная на себе: `ruff check --select RUF100` даёт 1617 вместо 556, потому что при одном выбранном правиле все noqa для остальных выглядят лишними. Мерить надо `--extend-select RUF100`, чтобы сохранить select проекта. Число 546 в постановке задачи было верным, а мой первый замер — нет.
- 2026-09-27T10:38:52Z [planning] — ПРЕДВАРИТЕЛЬНЫЙ ЗАМЕР (смена #277, до старта задачи). Всего RUF100: 556 при ПОЛНОМ select проекта. Раскол по формулировке ruff, и он определяет объём: 483 «unused» — правило ВКЛЮЧЕНО и не срабатывает (E402 458, F401 18, BLE001 7), это просто просрочено и снимается безопасно; 73 «non-enabled» — правило ВЫКЛЮЧЕНО (PLC0415 38, S608 7, SLF001 6, ANN001 5, ARG002 5, ARG001 4, S603 2, ANN201 2, N802 2, E402 1, S324 1), и их удаление есть СТАВКА на решение о расширении select, которое pyproject:284-296 прямо откладывает до отдельной задачи о 1539 находках ruff 0.16.1. Значит задача честно делится на 483 сейчас и 73 после того решения.
