---
slug: checklist-detector-is-red-on-its-own-test
title: "Детектор чек-листа СЛОМАН, и это доказано его собственным красным тестом на чистом HEAD"
status: planning
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

УСИЛИВАЕТ задачу verification-checklist-detector-misses-the-form-it-asked-for: там был симптом, здесь доказательство.

КРАСНЫЕ ТЕСТЫ НА ЧИСТОМ HEAD (проверено откатом всех правок сессии #157 через git stash):
- tests/test_checklist_hardgate.py::TestChecklistHardBlock::test_real_test_reference_clears_the_gate
- tests/test_checklist_hardgate.py::TestChecklistHardBlock::test_checklist_missing_reads_evidence_not_vocabulary

ЧТО ПОКАЗЫВАЕТ ОТКАЗ ДОСЛОВНО: checklist_missing({'acceptance_criteria': '1. does the thing\n2. errors on bad input', 'notes': '1. ✓ tests/test_real.py::test_a', 'relevant_files': '[]', 'tier': None}) возвращает True, тогда как тест требует False. То есть чек-лист С НАСТОЯЩЕЙ ССЫЛКОЙ НА ТЕСТ в форме файл::тест детектором НЕ ЗАСЧИТЫВАЕТСЯ.

ПОЧЕМУ ЭТО ХУЖЕ, ЧЕМ КРАСНЫЙ ТЕСТ. Гейт выдал предупреждение «checklist missing» ЧЕТЫРЕ раза подряд в сессиях #156-#157 на закрытиях, где чек-лист с поимёнными ссылками был записан ДО закрытия. Предупреждение, которое врёт, приучает себя игнорировать — и перестаёт работать в тех случаях, когда чек-листа действительно нет. Это утрата сигнала, а не неудобство.

ПОРЯДОК РАБОТ: сначала понять, ПОЧЕМУ красный тест был оставлен красным (он в наборе давно или сломан недавней правкой — проверить git log по scripts/, где живёт checklist_missing), потом чинить. Если тест был красным несколько сессий, это отдельный вопрос: значит полный прогон кто-то читал невнимательно, и это стоит записать памятью.

НЕГАТИВНЫЙ СЦЕНАРИЙ ОБЯЗАТЕЛЕН: задача БЕЗ чек-листа по-прежнему обязана получать предупреждение. Расширение распознавания не должно превратиться в «принимать что угодно» — иначе гейт перестанет отличать доказательство от его отсутствия, что хуже нынешнего состояния. Оба теста в test_checklist_hardgate.py именно про эту границу, их и надо привести в зелёное, а не ослабить.

## Acceptance Criteria

## Plan

## Rollback

## Journal
