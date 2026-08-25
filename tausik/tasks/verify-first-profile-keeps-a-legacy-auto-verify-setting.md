---
slug: verify-first-profile-keeps-a-legacy-auto-verify-setting
title: "Профиль Verify-First: auto_verify=true остаётся легаси-настройкой без решения"
status: planning
epic: arch-debt-post-18
story: adp18-quality-signals
complexity: simple
role: architect
stack: null
tier: light
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - ".tausik/config.json"
  - "docs/**"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Настройка task_done.auto_verify получает ЯВНОЕ решение — принята или изменена, а не висит вечным предупреждением doctor.

## Acceptance Criteria

1. doctor перестаёт выдавать WARN о профиле Verify-First: либо значение изменено, либо предупреждение снято решением, записанным как decision.
2. Решение опирается на замер, а не на вкус: сколько закрытий за последние N шло через verify → task done (интерактивный путь) и сколько инлайном.
3. НЕГАТИВНЫЙ: если auto_verify выключается, проверено, что односхаговый путь CI не ломается — иначе лечение переносит боль на конвейер.
4. НЕГАТИВНЫЙ: предупреждение не снимается отключением самой проверки в doctor. Гасить сигнал вместо причины — тот самый тихий отказ, который фреймворк ловит у других.

## Plan

## Rollback

вернуть прежнее значение в .tausik/config.json

## Journal
