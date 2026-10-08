---
slug: proektsiya-zadach-i-pamyati-est-69-protsentov
title: "Проекция задач и памяти есть 69 процентов дерева, и архивация её не уменьшает"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Замерить состав и цену проекции, назвать решение по каждому виду записью решения. Экспортёр НЕ меняется, если решение не потребует фильтра; фильтр archived_at в state_export — только при решении 'уходит', и тогда с круговым прогоном."
scope_exclude: null
relevant_files:
  - "scripts/projection_census.py"
  - "tests/test_projection_census.py"
  - "docs/en/state-projection-cost.md"
  - "docs/ru/state-projection-cost.md"
scope_paths:
  - "scripts/projection_census.py"
  - "tests/test_projection_census.py"
  - "docs/ru/state-projection-cost.md"
  - "docs/en/state-projection-cost.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on:
  - arhivatsiya-zadach-neobratima-komandy-snyat
completed_at: "2026-09-28T16:13:44Z"
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

Названо и замерено, из чего состоят 69 процентов дерева под git, и решено, уменьшать ли их. Архивация задач, на которую указывала история, проекцию не трогает: экспортёр выбирает FROM tasks без фильтра archived_at.

## Acceptance Criteria

1. Замер ДО: 3297 файлов проекции из 4776 под git, разбивка по видам (задачи, память, решения, истории, эпики). 2. Названа цена: что именно платит читатель и клон за каждый вид. 3. Решение по каждому виду: остаётся как есть, уходит за фильтр archived_at или сворачивается. 4. НЕГАТИВНЫЙ: если задачи уходят из дерева, круговой прогон state export плюс import на свежем клоне НЕ теряет ни одной задачи и метрики не меняются — иначе проекция перестаёт быть способом переносить состояние.

## Plan

## Rollback

git revert — добавляется скрипт замера, документ цены и запись решения; поведение экспортёра не меняется, если решение не скажет иначе. Если фильтр archived_at всё-таки будет добавлен в state_export, откат — тот же revert плюс tausik state export для перезаписи дерева; ни одна строка БД при этом не меняется, поэтому потери данных откат не несёт. Обратная операция скрытия задачи есть: tausik hygiene unarchive.

## Journal

- 2026-09-28T16:13:24Z [implementation] — AC-1 ЗАМЕР ДО: ✓ scripts/projection_census.py на живом дереве. Проекция 3317 из 4832 файлов под git = 68,6% путей и 47,1% байт (14 350 754 из 30 484 187). Разбивка: tasks 1744 файла / 11 933 248 Б / 39,1% дерева; memory 765 / 1 465 331 / 4,8%; decisions 401 / 655 171 / 2,1%; stories 297 / 102 467 / 0,3%; epics 109 / 36 786 / 0,1%; graph-snapshots 1 / 157 751 / 0,5%. Журналы — 47,8% байт файлов задач (5 707 404). За всю историю проекция = 48,7% касаний файлов, но 14,8% строкового churn.
- 2026-09-28T16:13:24Z [implementation] — AC-2 ЦЕНА НАЗВАНА: ✓ docs/{ru,en}/state-projection-cost.md — таблица замера, доля каждого вида, два числа про историю и рычаг. Клон и читатель платят 68,6% путей при 47,1% байт: цена в ЧИСЛЕ ФАЙЛОВ, не в объёме. Публичный снапшот проекцию исключает целиком (#368), поэтому потребитель фреймворка не платит ничего — цену несёт только линия разработки. AC-3 РЕШЕНИЕ ПО КАЖДОМУ ВИДУ: ✓ решение #402, все шесть — ОСТАЁТСЯ. Предпосылка опровергнута дважды: архивация проекцию не трогает (state_export выбирает FROM tasks без фильтра archived_at) и достижимый потолок 917 файлов = 19,0% путей, не 69%.
- 2026-09-28T16:13:25Z [implementation] — AC-4 НЕГАТИВНЫЙ не применим по конструкции и это ЗАКРЕПЛЕНО, а не пропущено: задачи из дерева НЕ уходят, поэтому кругового прогона export+import не требуется. Причина — .tausik/tausik.db в .gitignore: дерево есть единственный носитель состояния между машинами, и строка, выброшенная из дерева, теряется на свежем клоне. Оба факта держит tests/test_projection_census.py::TestTheTreeIsTheOnlyCarrier — test_the_database_does_not_travel и test_the_exporter_still_has_no_archived_at_filter_on_tasks. Если база начнёт ездить с деревом, тест покраснеет и решение придётся принимать заново: именно тогда круговой прогон становится обязательным. Domain: перепись отработала на живом дереве, числа в документе — её вывод, не пересказ. Лента 12090 прошли, 30 пропущены (было 12068). Храповика на долю НЕТ намеренно.
