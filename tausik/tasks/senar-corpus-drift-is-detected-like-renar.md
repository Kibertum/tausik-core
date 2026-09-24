---
slug: senar-corpus-drift-is-detected-like-renar
title: "Дрейф стандарта SENAR обнаруживается машиной, как у RENAR: редакция, число правил Core, имена гейтов, буквы свойств"
status: done
epic: release-110-deferred-from-19
story: release110-senar-15-claimed-honestly
complexity: medium
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/senar_standard_drift.py"
  - "scripts/project_cli_drift.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/project_parser.py"
  - "tests/test_senar_standard_drift.py"
scope_paths:
  - "scripts/senar_standard_drift.py"
  - "scripts/renar_standard_drift.py"
  - "scripts/project_cli_*.py"
  - "scripts/project_parser*.py"
  - "scripts/service_doctor*.py"
  - "scripts/project_config.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T18:50:41Z"
---

## Goal

renar_standard_drift читает корпус RENAR и находит расхождения закрытых списков и версии; для SENAR такого детектора нет, и о выходе 1.4 (04.09) и 1.5 (07.09) TAUSIK узнал из разговора владельца 23.09 — тот самый класс «узнали чтением спустя недели», ради которого детектор RENAR писался (решение о standards-drift-detection в 1.9). Цель: ключ конфига senar_standard_corpus (путь к standards/senar или standard-src), детектор парсит из текста: версию Core и Стандарта (баннеры), число правил Core, имена гейтов Core, буквы свойств 8.6 и их шкалу по конфигурациям, верхнюю выпущенную версию CHANGELOG; сравнивает с нашим заявлением (README/матрица) и печатает находки тремя состояниями: NO CORPUS, UNREADABLE, DRIFT.

## Acceptance Criteria

1. Детектор на живом корпусе (standards/senar/standard-src, ветка 1.5) находит расхождение «заявлено 1.3, корпус выпустил 1.5» и печатает, какие версии между ними вышли (из CHANGELOG корпуса).
2. НЕГАТИВНЫЙ: отсутствующий путь — NOT CHECKED с текстом, а не пустой список; путь без core/ и standard/ — UNREADABLE с именем недостающего.
3. НЕГАТИВНЫЙ: поддельный корпус с иным числом правил Core — находка; корпус с нашей редакцией — тишина.
4. tausik doctor показывает строку SENAR corpus; tausik drift --detector senar и drift all включают его со строкой статуса.
5. docs/ru+en (drift/doctor/configuration); CHANGELOG EN+RU.

## Plan

## Rollback

git revert; ключ конфига необязателен.

## Journal

- 2026-09-23T18:49:59Z [implementation] — AC verified: 1. ✓ test_an_older_claim_names_the_releases_since (заявка 1.3 против корпуса 1.5 — находка с перечнем версий из CHANGELOG корпуса); живой корпус: после перехода заявления на 1.5 detector печатает 'checked … (released 1.5)' без находки 2. ✓ test_no_corpus_is_not_checked_and_says_so, test_a_path_without_the_parsed_files_is_unreadable 3. ✓ test_a_different_core_rule_count_is_a_finding, test_a_corpus_matching_the_claim_is_silent 4. ✓ doctor: 'OK SENAR corpus … released v1.5'; drift --detector senar печатает строку статуса 5. ✓ docs drift/doctor/configuration en+ru, CHANGELOG EN+RU. Verify #2730 зелёный.
