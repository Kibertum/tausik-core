---
slug: qg0-negative-detector-russian-parity
title: "QG-0 negative-scenario detector: русское 'негатив' не распознаётся"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 12
defect_of: null
scope: "scripts/gate_negative_scenario.py (список ключевых слов), tests/test_senar.py или новый tests/test_negative_scenario_parity.py"
scope_exclude: "redaction/negation-логика; gate_qg0_check; ac_evidence_detectors"
relevant_files:
  - "scripts/gate_negative_scenario.py"
  - "tests/test_negative_scenario_parity.py"
  - "tests/test_senar.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-25T11:29:19Z"
---

## Goal

Детектор NEGATIVE_SCENARIO_KEYWORDS (gate_negative_scenario.py) знает английское 'negative' и НЕ знает русского 'негатив'; плюс ряд английских маркеров без русской пары (timeout, exception, crash, exceed, overflow). Русскоязычная задача со словом 'НЕГАТИВ' заваливает QG-0. Поймано догфудингом на state-git-export. Выровнять по паритету (конвенция #170), аддитивно, не трогая redaction 'без/no'.

## Acceptance Criteria

1. has_negative_scenario('5. НЕГАТИВ: сущность без слага -> экспорт отказывает') == True (русское 'негатив' распознаётся). 2. Паритет: у каждого добавленного русского маркера есть английская пара уже в списке; добавлены как минимум негатив, таймаут, исключени, паден (crash), превыш/переполн. 3. НЕГАТИВ/регрессия: has_negative_scenario('1. Работает. 2. Без ошибок.') остаётся False — redaction 'без' не сломан. 4. НЕГАТИВ/граница: has_negative_scenario('Works without any errors') остаётся False. 5. Существующий test_senar негативный набор зелёный. 6. Полный scoped verify зелёный.

## Plan

## Rollback

## Journal

- 2026-07-25T11:27:51Z [implementation] — AC verified (run #1316): AC-1: has_negative_scenario('5. НЕГАТИВ: сущность без слага -> экспорт отказывает') True — test_the_dogfood_case_that_exposed_it. AC-2 паритет: добавлены негатив/таймаут/исключени/паден/крах/превыш/переполн, каждый зеркалит английский маркер уже в списке; TestParityWithEnglish.test_same_verdict_in_both_languages. AC-3 регрессия: has_negative_scenario('1. Работает. 2. Без ошибок.') остаётся False — test_bez_oshibok_is_not_a_scenario. AC-4 граница: 'Works without any errors'/'without crashing'/'No failures' остаются False — test_without_errors_is_not_a_scenario. AC-5: test_senar 69 passed (весь набор зелёный). AC-6: verify #1316 exit=0. Negative: 'сбо' НЕ добавлен намеренно (матчил бы сбор/сборка/сбоку -> ложное срабатывание, ослабляющее гейт); test_a_plain_positive_criterion_is_not_a_scenario пинит это. Domain: реальная русскоязычная задача, честно описавшая негативный сценарий словом НЕГАТИВ, теперь проходит QG-0 так же, как её английский эквивалент — гейт перестал наказывать за язык проекта.
- 2026-07-25T11:29:17Z [implementation] — AC verified (run #1316). Added Russian parity keywords негатив/таймаут/исключени/паден/крах/превыш/переполн mirroring existing English markers; 'сбо' deliberately excluded (false-positive on сбор/сборка). Negative: 'Без ошибок' stays False (redaction intact); test_senar 69 passed. Domain: a Russian task naming its negative case as НЕГАТИВ now passes QG-0 like its English equivalent. CHANGELOG EN+RU added.
