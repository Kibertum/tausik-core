---
slug: release-notes-language-policy-is-unstated
title: "Процедура выпуска не говорит, на каком языке живут заметки к тегу — и 1.8 вышел одноязычным"
status: done
epic: release-110-deferred-from-19
story: release110-the-update-reaches-the-user
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/release_notes.py"
  - "scripts/project_cli_publish.py"
  - "scripts/project_parser_publish.py"
  - "docs/en/publishing.md"
  - "docs/ru/publishing.md"
  - "tests/test_release_notes.py"
scope_paths:
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "tests/*.py"
  - "scripts/release_notes.py"
  - "scripts/project_cli_publish.py"
  - "scripts/project_parser_publish.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T19:10:22Z"
---

## Goal

Процедура выпуска называет ЯВНО, где живут заметки к тегу на каждом языке: одноязычное тело тега со ссылкой на двуязычные whats-new — это осознанный выбор, зафиксированный текстом, а не то, что выяснилось постфактум при сверке 1.8.

## Acceptance Criteria

AC1. В процедуре выпуска (docs/{ru,en}) сказано ОДНОЙ ФРАЗОЙ, что тело тега ведётся на английском, а полный двуязычный текст — в docs/{ru,en}/whats-new-<version>.md, и тег ОБЯЗАН нести ссылку на обе страницы.
AC2. Требование проверяемо: тест или гейт при сборке тега убеждается, что тело тега содержит ссылку на обе страницы whats-new. Правило без проверки — это пожелание.
AC3. НЕГАТИВНЫЙ СЦЕНАРИЙ: проверка обязана СНАЧАЛА ПОКРАСНЕТЬ на теге v1.8.0 в его нынешнем виде — он ссылается на обе страницы, поэтому красным должен быть искусственный случай тега БЕЗ русской ссылки. Тест, зелёный на любом входе, ничего не стережёт.
AC4. Задача НЕ переписывает и НЕ перевыпускает тег v1.8.0: правило действует со следующего выпуска. Перевыпуск опубликованного тега хуже пробела, который он лечит.

## Plan

## Rollback

git revert коммита: правка чисто документационная

## Journal

- 2026-09-23T19:01:56Z [implementation] — Сделано: scripts/release_notes.py (whats_new_page, missing_links); tausik publish notes --version --body-file отказывает телу без ссылки на любую из страниц whats-new; шаг 4 в docs/en|ru/publishing.md одной фразой. С 1.9 тег на GitHub лёгкий, поэтому 'тело тега' = тело GitHub Release; тело v1.9.0 снято с GitHub и зелёное. AC verified: 1. ✓ publishing.md en/ru, test_the_procedure_states_the_rule_and_names_the_check 2. ✓ publish notes + test_the_cli_refuses_a_body_missing_a_page / test_the_cli_accepts_a_body_with_both_pages 3. ✓ НЕГАТИВНЫЙ: test_a_body_without_the_russian_page_is_refused (тело 1.9.0 без русской ссылки — отказ) 4. ✓ тег v1.8.0 и релиз v1.9.0 не трогались. 10 тестов зелёные.
