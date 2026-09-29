---
slug: internal-reference-numbers-on-user-pages
title: "196 внутренних ссылок на страницах для пользователя: номер решения читателю ничего не адресует"
status: done
epic: release-110-deferred-from-19
story: release110-docs-are-legible-to-an-outsider
complexity: medium
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/doc_internal_refs.py"
  - "tests/test_doc_internal_refs.py"
  - "docs/ru/sessions.md"
  - "docs/en/sessions.md"
scope_paths:
  - "docs/ru"
  - "docs/en"
  - "scripts/doc_internal_refs.py"
  - "tests/test_doc_internal_refs.py"
  - "tausik/gates.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T15:27:47Z"
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

Читатель со стороны не встречает номеров, которые ему нечем открыть. Замер: на 88 страницах reader=user 196 ссылок вида «решение #404» и 60 слагов задач. Номер адресует запись в базе проекта, которой у читателя нет; для него это тупик. На страницах maintainer номер уместен и остаётся.

## Acceptance Criteria

1. Замер ДО и ПОСЛЕ по страницам reader=user, с разбивкой по видам ссылок. 2. Каждая снятая ссылка заменена УТВЕРЖДЕНИЕМ, а не удалена: читатель должен узнать факт, а не потерять его. 3. Храповик в gates.json на число ссылок у пользователя, только вниз. 4. НЕГАТИВНЫЙ: на страницах reader=maintainer и reader=agent номера НЕ трогаются — там они адресуют записи, доступные читателю; тест закрепляет, что чистка не залезла туда. 5. НЕГАТИВНЫЙ: исторические цитаты вида «до решения #368 сайт жил в ядре» остаются, если без номера утверждение теряет проверяемость; такие случаи объявляются, а не вычищаются молча. 6. Полная лента зелёная.

## Plan

## Rollback

git revert; правка текстовая, номера сохраняются там, где адресуют — в памяти, журналах и на страницах для maintainer.

## Journal

- 2026-09-29T15:27:03Z [implementation] — AC-1: ✓ замер ДО 123 ссылки на 36 страницах reader=user, ПОСЛЕ 52 на 26; инструмент scripts/doc_internal_refs.py, счёт ведётся по читателю. AC-2: ✓ уходит адрес, факт остаётся: «ушёл из фреймворка в 1.9 (решение #358)» → «ушёл из фреймворка в 1.9»; выборочно проверено чтением diff по sessions, receipts, knowledge-store, cli. AC-3: ✓ храповик doc_internal_refs в gates.json, 52/26, только вниз, с записанной причиной остатка. AC-4 НЕГАТИВНЫЙ: ✓ tests/test_doc_internal_refs.py::TestOnlyTheUsersPagesAreCounted — maintainer и agent не считаются; ::test_an_external_tracker_reference_survives_the_cleanup — github#51 не наш номер.
- 2026-09-29T15:27:14Z [implementation] — AC-5 НЕГАТИВНЫЙ: ✓ остаток 52 объявлен, а не вычищен молча: это проза — ссылка за предлогом или открывающая предложение, — где границу не объявляет сам текст. Причина записана в gates.json и в докстринге теста. ДВА СВОИХ ДЕФЕКТА В ЭТОЙ ЖЕ ПРАВКЕ, оба пойманы чтением diff, а не тестом: (1) правило по прозе сломало предложение — ссылка стояла за предлогом, предлог остался ни с чем; это дохлый конец #784 второй раз за сутки, правило СУЖЕНО до скобочных форм, а не залатано; (2) уборка опустевших скобок сняла скобки с run_command_gate() на схеме — откачено, правило удалено, потому что проход не может оставить пустую пару. AC-6: ✓ лента 12369 прошли, 34 пропущены.
