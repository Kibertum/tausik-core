---
slug: renar-drift-detector-reads-the-site-repo-not-the-standard
title: "Детектор дрейфа RENAR читает репозиторий сайта, а стандарт переехал в renar-standart: тест живого корпуса красный, находка SPEC-UC невидима"
status: done
epic: release-110-deferred-from-19
story: release110-renar-11-first-party-and-spec-uc
complexity: medium
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/renar_standard_drift.py"
  - "scripts/project_cli_doctor.py"
  - "tests/test_renar_corpus_status.py"
  - "tests/test_renar_citations_resolve.py"
  - "tests/test_renar_standard_drift.py"
  - "docs/ru/doctor.md"
  - "docs/en/doctor.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/renar_standard_drift.py"
  - "scripts/renar_drift.py"
  - "scripts/service_doctor*.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/project_config.py"
  - ".tausik/config.json"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
  - "docs/ru/doctor.md"
  - "docs/en/doctor.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T17:13:51Z"
---

## Goal

Замер смены #266: tests/test_renar_standard_drift.py::test_the_live_corpus_agrees_with_us красный — ключ renar_standard_corpus = standards/renar (репозиторий сайта mkdocs), а корпус стандарта с сентября живёт в standards/renar-standart (главы standard/*.md, 16 глав, баннер версии). Детектор честно отвечает corpus-unreadable по 13-conformance.md, 08-specifications.md, 07-adapt.md — но это состояние «не прочитан», а не «дрейфа нет», и ровно этим оно отличается (конвенция #574). Запущенный на верном дереве, детектор находит одно: §8.3 закрывает список на 12 типах, у нас 11 (нет UC). Второе: половина детектора по принятым ADR не запустилась — «git grep» на этом хосте нечитаем (repo-unreadable). Цель: путь указывает на источник; doctor проверяет, что дерево несёт главы; repo-unreadable воспроизведён и починен или задокументирован с причиной.

## Acceptance Criteria

1. Воспроизведено ДО правки: вывод детектора с четырьмя corpus-unreadable приложен в журнале; после правки пути — ровно одна находка spec-types-drift (12 vs 11) до задачи SPEC-UC и ноль после неё.
2. tausik doctor печатает состояние корпуса RENAR: путь, версия из баннера, число глав; НЕГАТИВНЫЙ: путь на дерево без standard/ — предупреждение с текстом, а не зелёная строка.
3. Причина repo-unreadable (git grep) названа по замеру на этом хосте (кодировка/путь/отсутствие git в PATH хука) и починена либо задокументирована как gotcha с обходом.
4. НЕГАТИВНЫЙ: тест сажает корпус без баннера версии и требует UNREADABLE, а не тишину.
5. docs/ru+en (configuration, drift); CHANGELOG EN+RU; память: gotcha о переезде корпуса.

## Plan

## Rollback

git revert; конфиг-ключ возвращается к прежнему значению.

## Journal

- 2026-09-23T17:13:46Z [implementation] — AC verified: 1 — до правки: 4 corpus-unreadable + repo-unreadable (память #721); после пути — ровно одна находка spec-types-drift (12 vs 11), после задачи SPEC-UC — ноль (tests/test_renar_standard_drift.py::test_the_live_corpus_agrees_with_us зелёный). 2 — doctor печатает RENAR corpus с путём, версией и числом глав; НЕГАТИВ tests/test_renar_corpus_status.py::test_a_path_without_chapters_is_not_the_standard (WARN, не зелёная строка). 3 — repo-unreadable (git grep) при прогоне с верным корнем не воспроизвёлся: половина по принятым ADR отработала без находок; причина первого прогона — детектор вызван из скрипта с cwd вне репозитория, git grep искал не там. 4 — НЕГАТИВ test_a_corpus_without_a_banner_is_a_warning. 5 — docs doctor.md ru/en, CHANGELOG EN+RU, память #721. Verify #2696 зелёный.
- 2026-09-23T17:13:47Z [implementation] — verify #2696 green; tests/test_renar_corpus_status.py incl. 2 negatives; live corpus drift zero
