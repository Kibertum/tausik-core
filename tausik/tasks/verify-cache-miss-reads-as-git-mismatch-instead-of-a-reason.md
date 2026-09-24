---
slug: verify-cache-miss-reads-as-git-mismatch-instead-of-a-reason
title: "Отказ verify печатает cache_status=git-mismatch вместо содержательной причины: симптом сессии #152 чинится отдельно и дешевле"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/verify_cached_run.py"
  - "scripts/render_verify.py"
  - "tests/test_verify_status_explained.py"
  - "tests/test_service_verification.py"
  - "tests/test_verify_scope_honesty.py"
scope_paths:
  - "scripts/verify_cached_run.py"
  - "scripts/render_verify.py"
  - "scripts/verify_scope_honesty.py"
  - "harness/claude/mcp/project/handlers_verification.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T18:34:32Z"
---

## Goal

Выделено исследованием сессии #155 (решение #218). Это ТОТ САМЫЙ симптом, ради которого затевался разбор сессий: «verify дважды вернул cache_status=git-mismatch» назван поводом в решении #208.

СУТЬ: симптом НЕ решается переходом на хендл. Он вообще не про состояние с TTL — это отдельный дефект ФОРМУЛИРОВКИ отказа в scripts/verify_cached_run.py:353-358. Строка «git-mismatch» читается как промах кэша (то есть «попробуй ещё раз»), тогда как на деле она означает содержательное расхождение объявленной области с рабочим деревом.

ПОЧЕМУ ОТДЕЛЬНОЙ ЗАДАЧЕЙ: смешивать это с v2-verify-receipt-as-argument нельзя. Та задача меняет МЕХАНИЗМ (поиск по свежести -> точечный lookup по хендлу), эта — ТЕКСТ и классификацию отказа. Первая дорогая и рискованная, вторая дешёвая и безопасная. Если их слить, дешёвая починка окажется заложницей дорогой, а симптом, который видит пользователь, продолжит жить.

ЧТО ИМЕННО ПОЧИНИТЬ: отказ обязан НАЗЫВАТЬ причину — какие файлы разошлись, объявлены ли они, что делать. «git-mismatch» без разбора не даёт ни одного из трёх ответов и потому провоцирует повтор той же команды, который снова не сработает.

## Acceptance Criteria

1. Статус, который ставился как git-mismatch, называется scope-narrower-than-diff и в заголовке отчёта verify сопровождается фразой: кэш отказан, потому что N изменённых файлов не объявлены; сам прогон состоялся; что сделать (объявить файлы через --relevant-files).
2. Тест воспроизводит: область уже диффа → статус scope-narrower-than-diff и пояснение с числом необъявленных файлов.
3. НЕГАТИВНЫЙ: при совпадающей области статус остаётся miss/hit, пояснение не печатается.
4. Потребители значения (тесты, docs verify-glossary) обновлены; CHANGELOG EN+RU.

## Plan

## Rollback

git revert; a status string and its rendering

## Journal

- 2026-09-23T18:34:26Z [implementation] — AC verified: 1. ✓ SCOPE_NARROWER='scope-narrower-than-diff', render_verify._status_explained печатает число необъявленных файлов, 'прогон состоялся', 'объяви через --relevant-files' (виден в живых отчётах verify этой смены) 2. ✓ test_the_status_names_what_happened_and_what_to_do 3. ✓ test_a_consistent_scope_gets_no_explanation 4. ✓ test_the_old_name_is_gone; docs/en|ru/verify-glossary.md — новая строка термина; CHANGELOG EN+RU. Verify #2723 зелёный.
