---
slug: senar-v15-is-not-published-on-github
title: "Выпуск 1.10 заблокирован собственным гейтом: заявленная редакция SENAR v1.5 не опубликована на GitHub"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: architect
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/senar_claim.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-29T14:44:25Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 1
token_budget: null
cost_budget_usd: null
---

## Goal

tausik publish senar-check отвечает OK, и 1.10 можно тегировать. Сейчас гейт ОТКАЗЫВАЕТ: TAUSIK заявляет SENAR v1.5 Core в четырёх местах, а на GitHub Kibertum/SENAR опубликован только v1.3. Тег v1.5 существует и запушен на GitLab (3412fbb), но у репозитория стандарта нет настроенного remote на GitHub — публикация туда акт владельца в ЧУЖОМ репозитории.

## Acceptance Criteria

1. tausik publish senar-check печатает OK для заявленной редакции. 2. НЕГАТИВНЫЙ: заявление TAUSIK НЕ понижается до v1.3 ради прохождения гейта — публикуется редакция, а не переписывается claim; понижение сделало бы матрицу соответствия и четыре места заявления ложью. 3. Проверено на живом вызове, а не по факту наличия тега локально: гейт спрашивает GitHub, и локальный тег на GitLab его не удовлетворяет.

## Plan

## Rollback

## Journal

- 2026-09-29T14:43:35Z [implementation] — AC-1: ✓ tausik publish senar-check печатает OK: «SENAR v1.5, the edition TAUSIK claims, is published (tag for 1.5 found)». AC-2 НЕГАТИВНЫЙ: ✓ заявление НЕ понижалось — DECLARED_SENAR_VERSION остался 1.5, фраза заявления прежняя, tests/test_senar_claim.py держит её дословно в четырёх местах. Опубликована редакция, а не переписан claim. AC-3: ✓ проверено живым вызовом git ls-remote --tags к github.com/Kibertum/SENAR в обход гейта: refs/tags/v1.5 -> ed4e5d1 (аннотированный, ^{} на 2d2bae5). До публикации тот же запрос отдавал только v1.3 — проверял дважды, включая три написания имени репозитория.
- 2026-09-29T14:44:11Z [implementation] — NO-DEAD-END: блокировка была не отказом подхода, а ожиданием акта владельца в чужом репозитории — публикации редакции стандарта на GitHub. Подход не менялся: гейт спрашивал GitHub и был прав, тег появился, гейт позеленел. Единственное, что стоит унести: проверять такие блокеры ПРЯМЫМ запросом, а не только через гейт, — я это сделал трижды, включая три написания имени репозитория, и это отсекло версию про кэш и про ошибку гейта.
