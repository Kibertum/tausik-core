---
slug: cli-error-hint-for-task-add-shows-the-wrong-signature
title: "Подсказка на ошибке task add печатает НЕВЕРНЫЙ синтаксис: три позиционных вместо одного, следование ей даёт вторую ошибку"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: medium
role: developer
stack: python
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
---

## Goal

НАЙДЕНО ЖИВЬЁМ В #199. Ошибочный вызов `tausik task add` печатает подсказку, которая САМА НЕВЕРНА, и следование ей даёт вторую ошибку.

ЧТО ПЕЧАТАЕТСЯ ПРИ ОШИБКЕ:
  examples:
    tausik task add <story-slug> <task-slug> "Title" --stack python --complexity medium --role developer
То есть три ПОЗИЦИОННЫХ аргумента.

ЧТО НА САМОМ ДЕЛЕ (tausik task add --help):
  usage: tausik task add [-h] [--story STORY_SLUG] [--slug SLUG] ... title
То есть ОДИН позиционный (title), а story и slug — ИМЕНОВАННЫЕ опции.

ЦЕНА ЗАМЕРЕНА, НЕ ПРЕДПОЛОЖЕНА: агент, следуя подсказке, получил ту же ошибку ВТОРОЙ раз подряд и разобрался только через --help. Подсказка не сокращает путь к исправлению, а удлиняет его — она хуже, чем отсутствие подсказки, потому что выглядит авторитетной.

ПОЧЕМУ ЭТО НЕ ОПЕЧАТКА В ТЕКСТЕ. Проект держит правило «не угадывай аргументы CLI — читай --help или docs/ru/cli.md». Подсказка на ошибке — ровно тот канал, которым правило и исполняется. Неверная подсказка подрывает механизм, а не строку.

ЧТО ПРОВЕРИТЬ ЗАОДНО (не предполагать — прогнать): совпадают ли примеры в блоках `examples:` ОСТАЛЬНЫХ подкоманд с их реальными сигнатурами. Дешёвый способ — сравнить машиной текст примера с argparse-сигнатурой для каждой подкоманды; несовпадение позиционных/именованных ловится автоматически. Это же даёт контроль, чтобы не разъехалось снова.

## Acceptance Criteria

## Plan

## Rollback

## Journal
