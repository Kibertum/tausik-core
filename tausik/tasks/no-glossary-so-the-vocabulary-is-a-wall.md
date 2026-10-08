---
slug: no-glossary-so-the-vocabulary-is-a-wall
title: "Словаря терминов нет: QG-0, храповик, обвязка и SENAR читателю негде расшифровать"
status: done
epic: release-110-deferred-from-19
story: release110-docs-are-legible-to-an-outsider
complexity: medium
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/ru/glossary.md"
  - "docs/en/glossary.md"
  - "tests/test_glossary.py"
  - "docs/ru/start-here-user.md"
  - "docs/en/start-here-user.md"
scope_paths:
  - "docs/ru/glossary.md"
  - "docs/en/glossary.md"
  - "docs/_generated/doc-map.md"
  - "tests/test_glossary.py"
  - "docs/ru/start-here-user.md"
  - "docs/en/start-here-user.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T15:13:16Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

У человека со стороны есть место, где расшифрованы термины фреймворка. Замер: на 88 страницах для читателя user 162 вхождения жаргона (QG-0, QG-2, SENAR, RENAR, храповик, обвязка, scope ACL, проекция), и ни одной страницы glossary, terms, concepts или faq не существует.

## Acceptance Criteria

1. docs/{ru,en}/glossary.md существует, несёт doc-map маркер reader=user и парный заголовок ссылок. 2. Каждый термин: одно предложение определения плюс где он применяется; без внутренних номеров решений в определении. 3. Термины взяты ЗАМЕРОМ по страницам для пользователя, а не придуманы — список покрывает то, что реально встречается. 4. НЕГАТИВНЫЙ: тест краснеет, если на страницах для пользователя появился термин из списка жаргона, которого нет в словаре — иначе словарь устареет молча. 5. start-here-user указывает на словарь первой ссылкой. 6. Полная лента зелёная.

## Plan

## Rollback

git revert; добавляется страница и тест, существующие страницы не переписываются.

## Journal

- 2026-09-29T15:12:48Z [implementation] — AC-1: ✓ docs/{ru,en}/glossary.md с маркером reader=user zone=getting-started, парный заголовок ссылок; tests/test_glossary.py::test_the_glossary_exists_and_is_marked_for_the_user. AC-2: ✓ восемнадцать терминов, у каждого одно предложение и где применяется. AC-3: ✓ список собран подсчётом по страницам пользователя: gate 715, slug 467, stack 350, QG-2 74, QG-0 66 — числа в REQUIRED_TERMS и на самой странице. AC-4 НЕГАТИВНЫЙ: ✓ ::test_a_new_term_on_a_user_page_is_caught читает СТРАНИЦЫ и краснеет на термине, который употребляется и не определён; плюс ::test_a_definition_carries_no_internal_reference_number. AC-5: ✓ ::test_start_here_points_at_it. AC-6: ✓ лента 12355 прошли, 34 пропущены.
