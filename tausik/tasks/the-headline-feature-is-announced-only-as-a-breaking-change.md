---
slug: the-headline-feature-is-announced-only-as-a-breaking-change
title: "Главная фича 1.8 не объявлена там, где её ищут: общая база знаний есть только в ломающем изменении о переезде"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: tech-writer
stack: null
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: "scripts/**, tests/** — правится нарратив, не код"
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
completed_at: "2026-08-04T13:14:18Z"
---

## Goal

Читатель whats-new узнаёт, что в 1.8 появилась общая база знаний, из раздела «Что нового», а не выводит это из ломающего изменения о смене её адреса.

## Acceptance Criteria

1. Раздел «Что нового» обеих страниц whats-new открывается общей базой знаний: что это, зачем, как положить туда знание и где оно лежит.
2. Счёт ломающих изменений НЕ меняется и остаётся шесть во всех местах; проверяется tests/test_breaking_change_count_converges.py.
3. Тело GitHub Release переписано так, что первым идёт то же, что названо заголовком релиза, а не список ломающих.
4. НЕГАТИВНЫЙ сценарий: если правка случайно добавит или уберёт заголовок вида "### N." на странице whats-new, тест сходимости краснеет — счёт заголовков и число в прозе разойдутся.
5. НЕГАТИВНЫЙ сценарий: доковые гейты (docs_lint, audit_stale_docs) остаются зелёными; сломанная ссылка ЗАПРЕЩЕНА.

## Plan

## Rollback

git revert коммита; правки только в двух .md и в теле GitHub Release

## Journal

- 2026-08-04T13:13:45Z [implementation] — Чек-лист доказательств. AC-1 (раздел «Что нового» открывается общей базой): ✓ MANUAL: docs/ru/whats-new-1.8.md и docs/en/whats-new-1.8.md — подраздел «Общая база знаний — один файл на человека, а не на проект» / "A shared knowledge base" стоит ПЕРВЫМ в разделе, с командами --global и tausik search, с бэкапом, с отказом старого TAUSIK и с явным «чему тут не место» AC-2 (счёт ломающих не изменился): ✓ tests/test_breaking_change_count_converges.py::test_all_four_documents_state_the_same_number ✓ tests/test_breaking_change_count_converges.py::test_every_prose_statement_of_the_count_matches_the_sections AC-3 (тело GitHub Release ведёт фичей): ✓ MANUAL: gh release edit v1.8.0 применён; первым идёт «A shared knowledge base», затем конец серверной сессии и состояние в git, и только потом шесть ломающих AC-4 (негативный: заголовки не поехали): ✓ tests/test_breaking_change_count_converges.py::test_the_whats_new_sections_are_numbered_without_gaps — новые подразделы намеренно записаны как "### Общая база..." без номера, поэтому под _NUMBERED_SECTION не попадают; счёт остался шесть AC-5 (негативный: доковые гейты зелёные): ✓ MANUAL: docs_lint clean, audit_stale_docs «No stale docs detected. (OK)» Найдено ВЛАДЕЛЬЦЕМ при чтении changelog, не гейтом, и это стоит записать: гейты проверяют, что сказанное истинно и что копии согласованы. Ни один не умеет спросить, названо ли главное первым. Страница месяцами перечисляла, что чинили В общей базе, ни разу не сказав, что она появилась.
