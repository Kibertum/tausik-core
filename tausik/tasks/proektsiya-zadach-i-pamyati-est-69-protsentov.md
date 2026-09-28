---
slug: proektsiya-zadach-i-pamyati-est-69-protsentov
title: "Проекция задач и памяти есть 69 процентов дерева, и архивация её не уменьшает"
status: planning
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on:
  - arhivatsiya-zadach-neobratima-komandy-snyat
completed_at: null
resolution: null
resolution_reason: null
---

## Goal

Названо и замерено, из чего состоят 69 процентов дерева под git, и решено, уменьшать ли их. Архивация задач, на которую указывала история, проекцию не трогает: экспортёр выбирает FROM tasks без фильтра archived_at.

## Acceptance Criteria

1. Замер ДО: 3297 файлов проекции из 4776 под git, разбивка по видам (задачи, память, решения, истории, эпики). 2. Названа цена: что именно платит читатель и клон за каждый вид. 3. Решение по каждому виду: остаётся как есть, уходит за фильтр archived_at или сворачивается. 4. НЕГАТИВНЫЙ: если задачи уходят из дерева, круговой прогон state export плюс import на свежем клоне НЕ теряет ни одной задачи и метрики не меняются — иначе проекция перестаёт быть способом переносить состояние.

## Plan

## Rollback

## Journal
