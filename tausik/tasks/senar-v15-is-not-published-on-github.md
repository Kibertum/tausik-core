---
slug: senar-v15-is-not-published-on-github
title: "Выпуск 1.10 заблокирован собственным гейтом: заявленная редакция SENAR v1.5 не опубликована на GitHub"
status: blocked
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
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
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
