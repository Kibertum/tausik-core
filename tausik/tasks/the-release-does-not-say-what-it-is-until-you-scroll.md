---
slug: the-release-does-not-say-what-it-is-until-you-scroll
title: "Читатель узнаёт, чем является 1.8, только прокрутив README до низа и changelog до конца"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: tech-writer
stack: null
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: "docs/** — страницы whats-new уже переписаны отдельной задачей"
relevant_files:
  - README.md
  - README.ru.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/docs_lint.py"
  - "scripts/audit_stale_docs.py"
scope_paths:
  - README.md
  - README.ru.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-04T13:31:25Z"
---

## Goal

И README, и раздел [1.8.0] обоих changelog'ов называют суть выпуска ДО перечня: три опоры и шесть ломающих, прежде чем 165 записей.

## Acceptance Criteria

1. Раздел [1.8.0] обоих changelog'ов открывается абзацем, называющим три опоры выпуска и число ломающих, ДО первой записи ###.
2. README обоих языков называет общую базу знаний выше секции v1.8, которая лежит в самом низу: пункт «Что внутри» про память проекта говорит и про общее хранилище.
3. Счёт ломающих остаётся шесть во всех местах; проверяется tests/test_breaking_change_count_converges.py, который читает и число в прозе README.
4. НЕГАТИВНЫЙ сценарий: если вводный абзац случайно назовёт другое число ломающих, тест сходимости краснеет — именно для этого он читает прозу, а не только заголовки.
5. НЕГАТИВНЫЙ сценарий: доковые гейты docs_lint и audit_stale_docs остаются зелёными, сломанная ссылка ЗАПРЕЩЕНА.

## Plan

## Rollback

git revert коммита; правки только в четырёх .md

## Journal

- 2026-08-04T13:30:52Z [implementation] — Чек-лист доказательств. AC-1 (changelog открывается сутью): ✓ MANUAL: раздел [1.8.0] обоих файлов начинается абзацем «Общая база знаний, конец серверной сессии и состояние проекта в git. Шесть ломающих изменений» плюс тремя пунктами опор, и только потом идёт первая запись ### AC-2 (README называет общую базу выше секции v1.8): ✓ MANUAL: пункт «Общая база знаний (v1.8)» добавлен в «Что внутри» / "What's inside" обоих README — строка 126-131 против секции v1.8 на строке 188 AC-3 (счёт ломающих не изменился): ✓ tests/test_breaking_change_count_converges.py::test_every_prose_statement_of_the_count_matches_the_sections ✓ tests/test_breaking_change_count_converges.py::test_all_four_documents_state_the_same_number AC-4 (негативный: другое число в прозе краснит тест): ✓ MANUAL: вводный абзац changelog содержит «Шесть ломающих» / "Six breaking changes"; детектор _PROSE_COUNT читает и слово, и цифру, поэтому расхождение выявится. Проверено запуском — 42 теста зелёные. AC-5 (негативный: доковые гейты зелёные): ✓ MANUAL: docs_lint clean, audit_stale_docs «No stale docs detected. (OK)» Domain: проверяется чтением первого экрана, а не прогоном. Раньше читатель changelog видел первой записью «Python 3.13 сменил ntpath.isabs» — то есть первое впечатление от выпуска складывалось из починки пути под Windows. README называл общую базу знаний только в секции на строке 188, ниже «Методологии».
