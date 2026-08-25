---
slug: whats-new-opens-with-what-breaks-not-with-what-it-is
title: "Страница whats-new открывается списком поломок: читатель узнаёт, ЧТО такое 1.8, на 214-й строке"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: "README.md, README.ru.md — уже переписаны предыдущей задачей"
relevant_files:
  - "docs/ru/whats-new-1.8.md"
  - "docs/en/whats-new-1.8.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/docs_lint.py"
  - "scripts/audit_stale_docs.py"
scope_paths:
  - "docs/ru/whats-new-1.8.md"
  - "docs/en/whats-new-1.8.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-04T13:44:47Z"
---

## Goal

Читатель whats-new узнаёт суть выпуска в первом экране, до раздела ломающих изменений, — как это уже сделано в changelog и README.

## Acceptance Criteria

1. Обе страницы whats-new открываются блоком «что такое 1.8» — три опоры выпуска — ДО раздела ломающих изменений.
2. Назначение страницы сохранено: она остаётся для того, кто обновляется, и ломающие изменения по-прежнему идут ПОДРОБНО первым разделом, сразу за вводным блоком.
3. Счёт ломающих остаётся ШЕСТЬ во всех семи местах; проверяется tests/test_breaking_change_count_converges.py, который читает и число в прозе.
4. НЕГАТИВНЫЙ сценарий: вводный блок НЕ добавляет заголовков вида "### N." — иначе test_the_whats_new_sections_are_numbered_without_gaps увидит седьмую секцию и покраснеет.
5. НЕГАТИВНЫЙ сценарий: docs_lint и audit_stale_docs остаются зелёными, зеркальность RU и EN сохранена.

## Plan

## Rollback

git revert коммита; правки в двух .md

## Journal

- 2026-08-04T13:44:04Z [implementation] — Чек-лист доказательств. AC-1 (страницы открываются сутью выпуска): ✓ MANUAL: обе whats-new начинаются разделом «Что такое 1.8, в трёх пунктах» / "What 1.8 is, in three points" — общая база знаний, конец серверной сессии, состояние в git — ДО раздела ломающих AC-2 (назначение страницы сохранено): ✓ MANUAL: подзаголовок «для того, кто обновляется» остался; раздел ЛОМАЮЩИЕ ИЗМЕНЕНИЯ идёт сразу за вводным блоком, все шесть подробно, с ответом «касается ли это меня» AC-3 (счёт ломающих не изменился): ✓ tests/test_breaking_change_count_converges.py::test_every_prose_statement_of_the_count_matches_the_sections ✓ MANUAL: детектор прозы нашёл ровно четыре утверждения, все ШЕСТЬ; секций EN 6, RU 6 AC-4 (негативный: седьмой секции не появилось): ✓ tests/test_breaking_change_count_converges.py::test_the_whats_new_sections_are_numbered_without_gaps — вводный блок намеренно записан заголовками уровня ## и жирным текстом, без "### N." AC-5 (негативный: гейты и зеркальность): ✓ MANUAL: docs_lint clean, audit_stale_docs OK, 42 теста доковой группы зелёные; блоки RU и EN структурно идентичны Это ТРЕТИЙ случай одного промаха за день: changelog, README, whats-new. Первые два починены по указанию владельца, третий — тоже по его указанию. Форма промаха: правка «сказать главное первым» применялась к той двери, на которую показали, а не ко всем дверям в релиз. Записано в changelog отдельным абзацем, потому что это про способ работы, а не про текст страницы. Domain: проверяется чтением первого экрана. Раньше человек, открывший whats-new, первым делом читал «сначала шесть ломающих изменений», а про общую базу знаний узнавал на 214-й строке — если дочитывал.
